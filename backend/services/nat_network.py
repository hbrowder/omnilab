"""
NAT Network Service for OmniLab

CRE-56: Provides internet access to lab nodes via NAT
- Create/destroy Linux bridges
- Configure iptables MASQUERADE for SNAT
- Run dnsmasq for DHCP/DNS
- Health checks for connectivity

Development mode: Set OMNILAB_MOCK_NETWORK=1 to skip real infrastructure

Production deployment requires network admin privileges:
- Docker: Run container with --cap-add=NET_ADMIN
- Kubernetes: Set securityContext.capabilities.add: ["NET_ADMIN"]
- Bare metal: sudo setcap cap_net_admin+ep /path/to/python OR run as root
"""
import asyncio
import ipaddress
import os
import subprocess
from pathlib import Path

# Development mode: skip real bridge/iptables/dnsmasq operations
MOCK_MODE = os.getenv("OMNILAB_MOCK_NETWORK", "0") == "1"


class NetworkError(Exception):
    """NAT network operation errors"""
    pass


# Active dnsmasq processes: {bridge_name: subprocess}
_dnsmasq_processes: dict[str, asyncio.subprocess.Process] = {}

# Config directory for dnsmasq
DNSMASQ_CONF_DIR = Path("/tmp/omnilab-dnsmasq")
DNSMASQ_CONF_DIR.mkdir(parents=True, exist_ok=True)


def _run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """
    Run a shell command synchronously (for network setup commands that need immediate completion).

    Args:
        cmd: Command and arguments as list
        check: Raise exception on non-zero exit

    Returns:
        CompletedProcess result

    Raises:
        NetworkError: If command fails and check=True
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if check and result.returncode != 0:
            raise NetworkError(
                f"Command failed: {' '.join(cmd)}\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )
        return result
    except subprocess.TimeoutExpired:
        raise NetworkError(f"Command timed out: {' '.join(cmd)}") from None
    except Exception as e:
        raise NetworkError(f"Command error: {e}") from e


def bridge_exists(bridge_name: str) -> bool:
    """Check if a Linux bridge exists."""
    if MOCK_MODE:
        return False  # In mock mode, bridges never pre-exist
    result = _run_command(["ip", "link", "show", bridge_name], check=False)
    return result.returncode == 0


def create_bridge(bridge_name: str, subnet: str, gateway: str) -> None:
    """
    Create a Linux bridge and configure it with an IP address.

    Args:
        bridge_name: Bridge interface name (e.g., "br-nat0")
        subnet: Network subnet in CIDR (e.g., "192.168.100.0/24")
        gateway: Gateway IP address (e.g., "192.168.100.1")

    Raises:
        NetworkError: If bridge creation fails
    """
    if MOCK_MODE:
        # Mock mode: just validate inputs
        try:
            network = ipaddress.ip_network(subnet, strict=False)
            gw_ip = ipaddress.ip_address(gateway)
            if gw_ip not in network:
                raise NetworkError(f"Gateway {gateway} not in subnet {subnet}")
        except ValueError as e:
            raise NetworkError(f"Invalid subnet or gateway: {e}") from e
        return  # Skip actual bridge creation

    if bridge_exists(bridge_name):
        raise NetworkError(f"Bridge {bridge_name} already exists")

    # Validate subnet and gateway
    try:
        network = ipaddress.ip_network(subnet, strict=False)
        gw_ip = ipaddress.ip_address(gateway)
        if gw_ip not in network:
            raise NetworkError(f"Gateway {gateway} not in subnet {subnet}")
    except ValueError as e:
        raise NetworkError(f"Invalid subnet or gateway: {e}") from e

    # Create bridge
    _run_command(["ip", "link", "add", bridge_name, "type", "bridge"])

    # Assign IP address to bridge
    _run_command(["ip", "addr", "add", f"{gateway}/{network.prefixlen}", "dev", bridge_name])

    # Bring bridge up
    _run_command(["ip", "link", "set", bridge_name, "up"])


def delete_bridge(bridge_name: str) -> None:
    """
    Delete a Linux bridge.

    Args:
        bridge_name: Bridge interface name

    Raises:
        NetworkError: If bridge deletion fails
    """
    if MOCK_MODE:
        return  # Skip in mock mode

    if not bridge_exists(bridge_name):
        # Already gone - not an error
        return

    # Bring bridge down
    _run_command(["ip", "link", "set", bridge_name, "down"], check=False)

    # Delete bridge
    _run_command(["ip", "link", "delete", bridge_name], check=False)


def enable_ip_forwarding() -> None:
    """Enable IPv4 forwarding on the host (required for NAT)."""
    if MOCK_MODE:
        return
    _run_command(["sysctl", "-w", "net.ipv4.ip_forward=1"])


def configure_nat(bridge_name: str, subnet: str) -> None:
    """
    Configure iptables NAT (MASQUERADE) for a bridge.

    Args:
        bridge_name: Bridge interface name
        subnet: Network subnet in CIDR

    Raises:
        NetworkError: If NAT configuration fails
    """
    if MOCK_MODE:
        return

    # Enable IP forwarding
    enable_ip_forwarding()

    # Add MASQUERADE rule for SNAT (source NAT)
    # This allows packets from the lab subnet to reach the internet with the host's IP
    _run_command([
        "iptables", "-t", "nat", "-A", "POSTROUTING",
        "-s", subnet, "!", "-d", subnet,
        "-j", "MASQUERADE"
    ])

    # Allow forwarding from/to the bridge
    _run_command([
        "iptables", "-A", "FORWARD",
        "-i", bridge_name, "-j", "ACCEPT"
    ])
    _run_command([
        "iptables", "-A", "FORWARD",
        "-o", bridge_name, "-j", "ACCEPT"
    ])


def remove_nat(bridge_name: str, subnet: str) -> None:
    """
    Remove iptables NAT rules for a bridge.

    Args:
        bridge_name: Bridge interface name
        subnet: Network subnet in CIDR
    """
    if MOCK_MODE:
        return

    # Remove MASQUERADE rule
    _run_command([
        "iptables", "-t", "nat", "-D", "POSTROUTING",
        "-s", subnet, "!", "-d", subnet,
        "-j", "MASQUERADE"
    ], check=False)

    # Remove FORWARD rules
    _run_command([
        "iptables", "-D", "FORWARD",
        "-i", bridge_name, "-j", "ACCEPT"
    ], check=False)
    _run_command([
        "iptables", "-D", "FORWARD",
        "-o", bridge_name, "-j", "ACCEPT"
    ], check=False)


async def start_dnsmasq(
    bridge_name: str,
    subnet: str,
    gateway: str,
    dhcp_start: str,
    dhcp_end: str,
    dns_servers: list[str] = None,
) -> None:
    """
    Start dnsmasq for DHCP and DNS on a bridge.

    Args:
        bridge_name: Bridge interface name
        subnet: Network subnet in CIDR
        gateway: Gateway IP address
        dhcp_start: DHCP range start IP
        dhcp_end: DHCP range end IP
        dns_servers: List of upstream DNS servers (default: 8.8.8.8, 1.1.1.1)

    Raises:
        NetworkError: If dnsmasq fails to start
    """
    if MOCK_MODE:
        # Mock mode: just validate IPs
        if dns_servers is None:
            dns_servers = ["8.8.8.8", "1.1.1.1"]
        try:
            network = ipaddress.ip_network(subnet, strict=False)
            for ip_str in [gateway, dhcp_start, dhcp_end]:
                ip = ipaddress.ip_address(ip_str)
                if ip not in network:
                    raise NetworkError(f"IP {ip_str} not in subnet {subnet}")
        except ValueError as e:
            raise NetworkError(f"Invalid IP address: {e}") from e
        return

    if bridge_name in _dnsmasq_processes:
        raise NetworkError(f"dnsmasq already running for {bridge_name}")

    if dns_servers is None:
        dns_servers = ["8.8.8.8", "1.1.1.1"]

    # Validate IPs are in subnet
    try:
        network = ipaddress.ip_network(subnet, strict=False)
        for ip_str in [gateway, dhcp_start, dhcp_end]:
            ip = ipaddress.ip_address(ip_str)
            if ip not in network:
                raise NetworkError(f"IP {ip_str} not in subnet {subnet}")
    except ValueError as e:
        raise NetworkError(f"Invalid IP address: {e}") from e

    # Create dnsmasq config file
    conf_file = DNSMASQ_CONF_DIR / f"{bridge_name}.conf"
    conf_content = f"""# dnsmasq config for {bridge_name}
interface={bridge_name}
bind-interfaces
dhcp-range={dhcp_start},{dhcp_end},12h
dhcp-option=3,{gateway}
dhcp-option=6,{','.join(dns_servers)}
server={dns_servers[0]}
server={dns_servers[1]}
log-queries
log-dhcp
"""
    conf_file.write_text(conf_content)

    # Start dnsmasq
    try:
        process = await asyncio.create_subprocess_exec(
            "dnsmasq",
            "-C", str(conf_file),
            "--no-daemon",
            "--log-facility=-",  # Log to stderr
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait briefly to check if dnsmasq started successfully
        await asyncio.sleep(0.5)
        if process.returncode is not None:
            stderr_output = await process.stderr.read()
            raise NetworkError(f"dnsmasq failed to start: {stderr_output.decode('utf-8', errors='ignore')}")

        _dnsmasq_processes[bridge_name] = process

    except Exception as e:
        raise NetworkError(f"Failed to start dnsmasq: {e}") from e


async def stop_dnsmasq(bridge_name: str) -> None:
    """
    Stop dnsmasq for a bridge.

    Args:
        bridge_name: Bridge interface name
    """
    if MOCK_MODE:
        return

    if bridge_name not in _dnsmasq_processes:
        return  # Not running

    process = _dnsmasq_processes[bridge_name]

    try:
        if process.returncode is None:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
    except ProcessLookupError:
        pass  # Already gone

    del _dnsmasq_processes[bridge_name]

    # Clean up config file
    conf_file = DNSMASQ_CONF_DIR / f"{bridge_name}.conf"
    if conf_file.exists():
        conf_file.unlink()


async def create_nat_network(
    network_id: str,
    bridge_name: str,
    subnet: str,
    gateway: str,
    dhcp_start: str,
    dhcp_end: str,
    dns_servers: list[str] | None = None,
) -> dict:
    """
    Create a complete NAT network: bridge + NAT + DHCP/DNS.

    Args:
        network_id: Network UUID
        bridge_name: Bridge interface name (e.g., "br-nat0")
        subnet: Network subnet in CIDR (e.g., "192.168.100.0/24")
        gateway: Gateway IP address (e.g., "192.168.100.1")
        dhcp_start: DHCP range start IP
        dhcp_end: DHCP range end IP
        dns_servers: List of upstream DNS servers

    Returns:
        dict with network status

    Raises:
        NetworkError: If any step fails
    """
    try:
        # 1. Create bridge
        create_bridge(bridge_name, subnet, gateway)

        # 2. Configure NAT
        configure_nat(bridge_name, subnet)

        # 3. Start DHCP/DNS
        await start_dnsmasq(bridge_name, subnet, gateway, dhcp_start, dhcp_end, dns_servers)

        return {
            "network_id": network_id,
            "bridge_name": bridge_name,
            "subnet": subnet,
            "gateway": gateway,
            "dhcp_range": f"{dhcp_start}-{dhcp_end}",
            "dns_servers": dns_servers or ["8.8.8.8", "1.1.1.1"],
            "status": "active",
        }

    except Exception as e:
        # Rollback on failure
        await stop_dnsmasq(bridge_name)
        remove_nat(bridge_name, subnet)
        delete_bridge(bridge_name)
        raise NetworkError(f"Failed to create NAT network: {e}") from e


async def destroy_nat_network(bridge_name: str, subnet: str) -> None:
    """
    Destroy a NAT network: stop DHCP, remove NAT, delete bridge.

    Args:
        bridge_name: Bridge interface name
        subnet: Network subnet in CIDR
    """
    await stop_dnsmasq(bridge_name)
    remove_nat(bridge_name, subnet)
    delete_bridge(bridge_name)


def check_nat_health(bridge_name: str) -> dict:
    """
    Check health of a NAT network.

    Args:
        bridge_name: Bridge interface name

    Returns:
        dict with health status
    """
    if MOCK_MODE:
        return {
            "bridge_exists": True,
            "dnsmasq_running": True,
            "ip_forwarding_enabled": True,
            "status": "healthy (mock mode)",
        }

    health = {
        "bridge_exists": bridge_exists(bridge_name),
        "dnsmasq_running": bridge_name in _dnsmasq_processes,
        "ip_forwarding_enabled": False,
    }

    # Check IP forwarding
    result = _run_command(["sysctl", "net.ipv4.ip_forward"], check=False)
    if result.returncode == 0 and "= 1" in result.stdout:
        health["ip_forwarding_enabled"] = True

    health["status"] = "healthy" if all(health.values()) else "unhealthy"

    return health
