/**
 * RealtimeSyncContext — App-level React Context for WebSocket real-time events.
 *
 * Wrap your app with <RealtimeSyncProvider> and use useRealtimeEvent() in any component
 * to subscribe to specific events.
 */

import React, { createContext, useContext } from 'react';
import { useRealtimeSync } from '../hooks/useRealtimeSync';

type EventHandler = (data: any) => void;

interface RealtimeSyncContextValue {
    isConnected: boolean;
    onEvent: (eventType: string, handler: EventHandler) => () => void;
}

const RealtimeSyncContext = createContext<RealtimeSyncContextValue>({
    isConnected: false,
    onEvent: () => () => { },
});

export function RealtimeSyncProvider({ children }: { children: React.ReactNode }) {
    const sync = useRealtimeSync();

    return (
        <RealtimeSyncContext.Provider value={sync}>
            {children}
        </RealtimeSyncContext.Provider>
    );
}

/**
 * Hook to access the realtime sync context.
 * Returns { isConnected, onEvent }.
 */
export function useRealtimeSyncContext() {
    return useContext(RealtimeSyncContext);
}

/**
 * Hook to subscribe to a specific realtime event.
 * Auto-cleans up on unmount.
 *
 * Usage:
 *   useRealtimeEvent('styles_updated', (data) => { loadSavedStyles(); });
 */
export function useRealtimeEvent(eventType: string, handler: EventHandler) {
    const { onEvent } = useRealtimeSyncContext();

    React.useEffect(() => {
        const unsub = onEvent(eventType, handler);
        return unsub;
    }, [eventType, handler, onEvent]);
}
