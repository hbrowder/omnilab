"""
Traffic Service: Packet capture and real-time event emission.

CRE-68 Phase 3 Milestone 2: Packet Capture Integration
- Starts/stops tcpdump per filter
- Parses packet output in real-time
- Maps interfaces to link_id via topology_mapper
- Emits WebSocket events via traffic_websocket
- Maintains packet counters per filter
"""

import asyncio
import subprocess
import re
import time
from typing import Dict, Optional, Set, List
from dataclasses import dataclass, field
from threading import Thread, Lock

from services.topology_mapper import get_topology_mapper
from api.traffic_websocket import send_traffic_match, send_packet_count_update, send_filter_activated, send_filter_deactivated, send_error


@dataclass
class CaptureSession:
    """Active packet capture session for a filter."""
    filter_id: str
    lab_id: str
    expression: str  # BPF filter expression
    color: str
    processes: Dict[str, subprocess.Popen] = field(default_factory=dict)  # interface → process
    threads: Dict[str, Thread] = field(default_factory=dict)  # interface → reader thread
    interface_to_link: Dict[str, str] = field(default_factory=dict)  # interface → link_id
    packet_count: int = 0
    active: bool = True
    # Batching fields for throttling WebSocket events
    pending_events: List[Dict] = field(default_factory=list)
    last_batch_time: float = field(default_factory=lambda: time.time())
    batch_interval: float = 0.1  # Send batches every 100ms


class TrafficService:
    """Manages packet capture sessions and event emission."""
    
    def __init__(self):
        self._sessions: Dict[str, CaptureSession] = {}  # {filter_id: session}
        self._lock = Lock()
    
    async def start_capture(self, lab_id: str, filter_id: str, expression: str, color: str):
        """
        Start per-container packet capture for a filter.
        
        Uses 'docker exec <container> tcpdump -i <interface>' to capture traffic
        inside container namespaces where the interfaces actually exist.
        
        Args:
            lab_id: Lab identifier
            filter_id: Traffic filter ID
            expression: BPF filter expression (tcpdump syntax)
            color: Color for visualization
        """
        with self._lock:
            # Stop existing session if any
            if filter_id in self._sessions:
                await self.stop_capture(filter_id)
            
            try:
                # Get the current running event loop to pass to threads
                loop = asyncio.get_running_loop()
                
                # Get container-interface mappings from topology
                mapper = get_topology_mapper()
                container_interface_map = mapper.get_container_interfaces(lab_id)
                
                if not container_interface_map:
                    await send_error(lab_id, f"No container interfaces found for lab {lab_id}", filter_id)
                    return
                
                # Create session
                session = CaptureSession(
                    filter_id=filter_id,
                    lab_id=lab_id,
                    expression=expression,
                    color=color
                )
                
                # Build link_id lookup by (container, interface)
                # This allows _read_packets_from_interface to quickly find link_id
                session.interface_to_link = {
                    f"{container}:{iface}": link_id 
                    for (container, iface), link_id in container_interface_map.items()
                }
                
                # Start one tcpdump per (container, interface) pair
                for (container_name, interface), link_id in container_interface_map.items():
                    try:
                        # docker exec -t <container> tcpdump -i <interface> -n -l <expression>
                        # Note: -t flag allocates pseudo-TTY so stdout/stderr work properly
                        cmd = [
                            'docker', 'exec',
                            '-t',  # Allocate pseudo-TTY for proper stdout capture
                            container_name,
                            'tcpdump',
                            '-i', interface,
                            '-n',         # Don't resolve hostnames
                            '-l',         # Line buffered output
                            '-tt',        # Timestamp as Unix epoch
                            expression
                        ]
                        
                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            bufsize=1  # Line buffered
                        )
                        
                        # Check if process died immediately (container not running, permission error, etc.)
                        time.sleep(0.05)
                        if process.poll() is not None:
                            stderr = process.stderr.read() if process.stderr else ""
                            # Clean up already-started processes
                            for p in session.processes.values():
                                p.kill()
                            
                            # Provide helpful error messages for common failures
                            if "No such container" in stderr:
                                raise RuntimeError(
                                    f"Container {container_name} not running. "
                                    f"Start the lab nodes before enabling traffic filters."
                                )
                            elif "permission denied" in stderr.lower() or "operation not permitted" in stderr.lower():
                                raise RuntimeError(
                                    f"Permission denied running tcpdump in {container_name}. "
                                    f"The container needs CAP_NET_RAW capability. "
                                    f"Check Docker container privileges."
                                )
                            elif "no such device" in stderr.lower():
                                raise RuntimeError(
                                    f"Interface {interface} not found in {container_name}. "
                                    f"The container may still be starting up or the interface doesn't exist."
                                )
                            elif "tcpdump: command not found" in stderr or "executable file not found" in stderr:
                                raise RuntimeError(
                                    f"tcpdump not installed in {container_name}. "
                                    f"The container image must include tcpdump for traffic capture."
                                )
                            else:
                                raise RuntimeError(
                                    f"tcpdump failed in {container_name} on {interface}. "
                                    f"Error: {stderr[:200]}"
                                )
                        
                        # Use container:interface as key
                        key = f"{container_name}:{interface}"
                        session.processes[key] = process
                        
                        # Start reader thread for this container-interface pair
                        thread = Thread(
                            target=self._read_packets_from_interface,
                            args=(session, container_name, interface, loop),
                            daemon=True
                        )
                        thread.start()
                        session.threads[key] = thread
                        
                    except Exception as e:
                        # Clean up already-started processes
                        for p in session.processes.values():
                            p.kill()
                        raise RuntimeError(f"Failed to start capture on {container_name}:{interface}: {e}")
                
                self._sessions[filter_id] = session
                
                # Notify activation
                await send_filter_activated(lab_id, filter_id, expression, color, 10000)
                
            except FileNotFoundError:
                await send_error(lab_id, "docker or tcpdump not found", filter_id)
            except PermissionError:
                await send_error(lab_id, "Permission denied - check Docker daemon access", filter_id)
            except Exception as e:
                await send_error(lab_id, f"Failed to start capture: {e}", filter_id)
    
    async def stop_capture(self, filter_id: str):
        """Stop packet capture for a filter (all interfaces)."""
        with self._lock:
            session = self._sessions.pop(filter_id, None)
            if not session:
                return
            
            # Mark inactive
            session.active = False
            
            # Get event loop for final flush
            loop = asyncio.get_running_loop()
            
            # Flush any remaining pending events before stopping
            self._flush_batch(session, loop)
            
            # Terminate all processes
            for iface, process in session.processes.items():
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                except Exception:
                    pass
            
            # Wait for threads to finish
            for thread in session.threads.values():
                thread.join(timeout=1)
            
            # Notify deactivation
            await send_filter_deactivated(session.lab_id, filter_id)
    
    def _read_packets_from_interface(self, session: CaptureSession, container_name: str, interface: str, loop):
        """
        Read packets from tcpdump running inside a container (runs in background thread).
        
        Args:
            session: CaptureSession with processes and metadata
            container_name: Container name (e.g., "omnilab-209b6bf7...")
            interface: Interface name inside container (e.g., "eth0")
            loop: asyncio event loop to schedule coroutines on
        """
        key = f"{container_name}:{interface}"
        process = session.processes.get(key)
        if not process or not process.stdout:
            return
        
        # Get link_id for this container:interface pair
        link_id = session.interface_to_link.get(key)
        if not link_id:
            print(f"Warning: No link_id found for {key}, skipping capture")
            return
        
        def schedule_coro(coro):
            """Schedule a coroutine on the main event loop from this thread"""
            asyncio.run_coroutine_threadsafe(coro, loop)
        
        try:
            for line in process.stdout:
                if not session.active:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Increment packet counter
                session.packet_count += 1
                
                # Queue event instead of sending immediately
                event = {
                    "lab_id": session.lab_id,
                    "filter_id": session.filter_id,
                    "link_id": link_id,
                    "packet_summary": f"{container_name.split('-')[-1][:8]}:{interface}: {line[:80]}"
                }
                
                # Thread-safe batching with lock
                with self._lock:
                    session.pending_events.append(event)
                    
                    # Flush batch if interval elapsed
                    now = time.time()
                    if now - session.last_batch_time >= session.batch_interval:
                        self._flush_batch(session, loop)
                        session.last_batch_time = now
        
        except Exception as e:
            if session.active:
                schedule_coro(send_error(
                    session.lab_id, 
                    f"Capture error on {key}: {e}", 
                    session.filter_id
                ))
    
    def _flush_batch(self, session: CaptureSession, loop):
        """
        Flush pending events for a session.
        Sends up to 20 events per flush to avoid massive bursts.
        """
        if not session.pending_events:
            return
        
        # Send up to 20 events per batch (prevent massive bursts)
        batch = session.pending_events[:20]
        session.pending_events = session.pending_events[20:]
        
        # Import here to avoid circular dependency
        from api.traffic_websocket import send_traffic_batch
        
        # Send the entire batch as ONE WebSocket message
        future = asyncio.run_coroutine_threadsafe(
            send_traffic_batch(session.lab_id, batch),
            loop
        )
        try:
            future.result(timeout=0.5)
        except Exception as e:
            print(f"Failed to send batched events: {e}")
    
    def get_active_filters(self) -> Set[str]:
        """Get set of active filter IDs."""
        with self._lock:
            return set(self._sessions.keys())
    
    def get_packet_count(self, filter_id: str) -> int:
        """Get packet count for a filter."""
        with self._lock:
            session = self._sessions.get(filter_id)
            return session.packet_count if session else 0
    
    async def stop_all(self):
        """Stop all active captures."""
        with self._lock:
            filter_ids = list(self._sessions.keys())
        
        for filter_id in filter_ids:
            await self.stop_capture(filter_id)


# Global instance
_service = None

def get_traffic_service() -> TrafficService:
    """Get global traffic service instance."""
    global _service
    if _service is None:
        _service = TrafficService()
    return _service
