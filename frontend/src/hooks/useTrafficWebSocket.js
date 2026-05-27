/**
 * WebSocket hook for real-time traffic visualization events.
 * 
 * CRE-68 Phase 3: Connects to backend traffic WebSocket and manages
 * event stream for animated traffic flows.
 * 
 * @param {string} labId - Lab UUID
 * @returns {object} - { events, connected, packetCounts, activeFilters, sendMessage }
 */
import { useState, useEffect, useRef, useCallback } from 'react';

const WEBSOCKET_URL = process.env.REACT_APP_WS_URL || 'ws://192.168.174.132:9999';
const RECONNECT_DELAY = 3000; // 3 seconds
const MAX_EVENTS_IN_MEMORY = 100; // Keep last 100 events for debugging

export const useTrafficWebSocket = (labId) => {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState([]);
  const [packetCounts, setPacketCounts] = useState({}); // {filter_id: count}
  const [activeFilters, setActiveFilters] = useState(new Set()); // Set of active filter_ids
  const [lastError, setLastError] = useState(null); // Last WebSocket error message
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const shouldReconnectRef = useRef(true);

  // Send message to server (for ping, subscribe, etc.)
  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message:', message);
    }
  }, []);

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((event) => {
    try {
      const data = JSON.parse(event.data);
      const eventType = data.type;

      // Add to events history (keep last N events)
      setEvents(prev => {
        const newEvents = [...prev, { ...data, id: Date.now() + Math.random() }];
        return newEvents.slice(-MAX_EVENTS_IN_MEMORY);
      });

      // Handle specific event types
      switch (eventType) {
        case 'connected':
          console.log('✅ Traffic WebSocket connected:', data.message);
          break;

        case 'filter_activated':
          setActiveFilters(prev => new Set(prev).add(data.filter_id));
          console.log(`🟢 Filter activated: ${data.name} (${data.filter_id})`);
          break;

        case 'filter_deactivated':
          setActiveFilters(prev => {
            const newSet = new Set(prev);
            newSet.delete(data.filter_id);
            return newSet;
          });
          setPacketCounts(prev => {
            const newCounts = { ...prev };
            delete newCounts[data.filter_id];
            return newCounts;
          });
          console.log(`🔴 Filter deactivated: ${data.filter_id}`);
          break;

        case 'traffic_match':
          // This is the hot path - will trigger animations
          // Don't log every single packet (too noisy)
          break;

        case 'traffic_batch':
          // CRE-68 Phase 3 Milestone 4 Task 3: Handle batched events
          // Animation handled by LinkAnimationEngine
          // Packet counting handled by packet_count_update messages
          break;

        case 'packet_count_update':
          setPacketCounts(prev => ({
            ...prev,
            [data.filter_id]: data.count
          }));
          break;

        case 'error':
          console.error('❌ Traffic WebSocket error:', data.message, data.filter_id);
          setLastError(data.message);
          // Auto-clear error after 10 seconds
          setTimeout(() => setLastError(null), 10000);
          break;

        case 'heartbeat':
        case 'pong':
          // Silent heartbeat/pong
          break;

        default:
          console.warn('Unknown WebSocket event type:', eventType, data);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error, event.data);
    }
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!labId) {
      console.warn('Cannot connect: labId is null');
      return;
    }

    if (wsRef.current) {
      console.log('WebSocket already exists, skipping connect');
      return;
    }

    const wsUrl = `${WEBSOCKET_URL}/api/labs/${labId}/traffic-ws`;
    console.log('🔌 Connecting to traffic WebSocket:', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ Traffic WebSocket opened');
        setConnected(true);
        // Send ping on connect to verify bidirectional communication
        ws.send(JSON.stringify({ type: 'ping' }));
      };

      ws.onmessage = handleMessage;

      ws.onerror = (error) => {
        console.error('❌ Traffic WebSocket error:', error);
        setConnected(false);
      };

      ws.onclose = (event) => {
        console.log('🔌 Traffic WebSocket closed:', event.code, event.reason);
        setConnected(false);
        wsRef.current = null;

        // Auto-reconnect if not intentionally closed
        if (shouldReconnectRef.current && event.code !== 1000) {
          console.log(`🔄 Reconnecting in ${RECONNECT_DELAY / 1000}s...`);
          reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_DELAY);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setConnected(false);
    }
  }, [labId, handleMessage]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'Component unmounted');
      wsRef.current = null;
    }
    setConnected(false);
    setActiveFilters(new Set());
    setPacketCounts({});
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Heartbeat ping every 20 seconds to keep connection alive
  useEffect(() => {
    if (!connected) return;

    const pingInterval = setInterval(() => {
      sendMessage({ type: 'ping' });
    }, 20000);

    return () => clearInterval(pingInterval);
  }, [connected, sendMessage]);

  return {
    connected,
    events,
    packetCounts,
    activeFilters,
    lastError,
    sendMessage,
    disconnect
  };
};
