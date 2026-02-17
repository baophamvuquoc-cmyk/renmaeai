/**
 * useRealtimeSync — WebSocket hook for real-time app synchronization.
 *
 * Connects to ws://localhost:8000/ws, auto-reconnects with exponential backoff,
 * and dispatches events to registered listeners. Also syncs across browser tabs
 * via BroadcastChannel.
 *
 * Usage:
 *   const { isConnected, onEvent } = useRealtimeSync();
 *   onEvent('styles_updated', (data) => { loadSavedStyles(); });
 */

import { useEffect, useRef, useCallback, useState } from 'react';

const WS_URL = 'ws://localhost:8000/ws';
const HEARTBEAT_INTERVAL = 30_000; // 30s
const RECONNECT_BASE_DELAY = 1_000; // 1s
const RECONNECT_MAX_DELAY = 30_000; // 30s
const BROADCAST_CHANNEL_NAME = 'renmaeai-sync';

type EventHandler = (data: any) => void;

interface RealtimeSyncReturn {
    isConnected: boolean;
    onEvent: (eventType: string, handler: EventHandler) => () => void;
}

export function useRealtimeSync(): RealtimeSyncReturn {
    const [isConnected, setIsConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    const listenersRef = useRef<Map<string, Set<EventHandler>>>(new Map());
    const reconnectAttemptRef = useRef(0);
    const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const mountedRef = useRef(true);
    const bcRef = useRef<BroadcastChannel | null>(null);

    // ── Register event listener ──
    const onEvent = useCallback((eventType: string, handler: EventHandler): (() => void) => {
        if (!listenersRef.current.has(eventType)) {
            listenersRef.current.set(eventType, new Set());
        }
        listenersRef.current.get(eventType)!.add(handler);

        // Return unsubscribe function
        return () => {
            listenersRef.current.get(eventType)?.delete(handler);
        };
    }, []);

    // ── Dispatch event to listeners ──
    const dispatch = useCallback((eventType: string, data: any) => {
        const handlers = listenersRef.current.get(eventType);
        if (handlers) {
            handlers.forEach(handler => {
                try {
                    handler(data);
                } catch (err) {
                    console.error(`[RealtimeSync] Error in handler for '${eventType}':`, err);
                }
            });
        }
    }, []);

    // ── Start heartbeat ──
    const startHeartbeat = useCallback(() => {
        if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);
        heartbeatTimerRef.current = setInterval(() => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send('ping');
            }
        }, HEARTBEAT_INTERVAL);
    }, []);

    // ── Stop heartbeat ──
    const stopHeartbeat = useCallback(() => {
        if (heartbeatTimerRef.current) {
            clearInterval(heartbeatTimerRef.current);
            heartbeatTimerRef.current = null;
        }
    }, []);

    // ── Connect WebSocket ──
    const connect = useCallback(() => {
        if (!mountedRef.current) return;
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        try {
            const ws = new WebSocket(WS_URL);

            ws.onopen = () => {
                if (!mountedRef.current) { ws.close(); return; }
                console.log('[RealtimeSync] ✅ Connected');
                setIsConnected(true);
                reconnectAttemptRef.current = 0;
                startHeartbeat();
            };

            ws.onmessage = (event) => {
                if (event.data === 'pong') return; // Heartbeat response

                try {
                    const msg = JSON.parse(event.data);
                    if (msg.event) {
                        dispatch(msg.event, msg.data);
                        // Relay to other tabs via BroadcastChannel
                        bcRef.current?.postMessage({ event: msg.event, data: msg.data });
                    }
                } catch {
                    // Ignore non-JSON messages
                }
            };

            ws.onclose = () => {
                if (!mountedRef.current) return;
                console.log('[RealtimeSync] ❌ Disconnected');
                setIsConnected(false);
                stopHeartbeat();
                scheduleReconnect();
            };

            ws.onerror = () => {
                // onclose will fire after this
            };

            wsRef.current = ws;
        } catch (err) {
            console.error('[RealtimeSync] Connection error:', err);
            scheduleReconnect();
        }
    }, [dispatch, startHeartbeat, stopHeartbeat]);

    // ── Reconnect with exponential backoff ──
    const scheduleReconnect = useCallback(() => {
        if (!mountedRef.current) return;
        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);

        const attempt = reconnectAttemptRef.current;
        const delay = Math.min(RECONNECT_BASE_DELAY * Math.pow(2, attempt), RECONNECT_MAX_DELAY);
        reconnectAttemptRef.current = attempt + 1;

        console.log(`[RealtimeSync] Reconnecting in ${delay / 1000}s (attempt ${attempt + 1})...`);
        reconnectTimerRef.current = setTimeout(() => {
            connect();
        }, delay);
    }, [connect]);

    // ── BroadcastChannel for multi-tab sync ──
    useEffect(() => {
        try {
            const bc = new BroadcastChannel(BROADCAST_CHANNEL_NAME);
            bc.onmessage = (event) => {
                if (event.data?.event) {
                    dispatch(event.data.event, event.data.data);
                }
            };
            bcRef.current = bc;

            return () => {
                bc.close();
                bcRef.current = null;
            };
        } catch {
            // BroadcastChannel not supported (rare)
            console.warn('[RealtimeSync] BroadcastChannel not supported');
        }
    }, [dispatch]);

    // ── Connect on mount, cleanup on unmount ──
    useEffect(() => {
        mountedRef.current = true;
        connect();

        return () => {
            mountedRef.current = false;
            stopHeartbeat();
            if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
            if (wsRef.current) {
                wsRef.current.onclose = null; // Prevent reconnect on unmount
                wsRef.current.close();
            }
        };
    }, [connect, stopHeartbeat]);

    return { isConnected, onEvent };
}
