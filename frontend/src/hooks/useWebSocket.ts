import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuthStore } from '@/store/authStore';
import { useMarketStore } from '@/store/marketStore';

interface WebSocketMessage {
  type: string;
  data?: any;
  symbol?: string;
  timestamp?: string;
  request_id?: string;
}

interface UseWebSocketOptions {
  url?: string;
  autoConnect?: boolean;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const {
    url = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8002',
    autoConnect = true,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectCountRef = useRef(0);
  const messageQueueRef = useRef<string[]>([]);
  
  const { tokens } = useAuthStore();
  const { updateQuote } = useMarketStore();

  // Message handlers
  const messageHandlers = useRef<Map<string, (data: any) => void>>(new Map());

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionState('connecting');
    setError(null);

    try {
      const wsUrl = tokens?.access_token 
        ? `${url}/v1/ws/ws?token=${tokens.access_token}`
        : `${url}/v1/real-time/ws`;
      
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        setConnectionState('connected');
        setError(null);
        reconnectCountRef.current = 0;

        // Send queued messages
        while (messageQueueRef.current.length > 0) {
          const message = messageQueueRef.current.shift();
          if (message && wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(message);
          }
        }
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          handleMessage(message);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      wsRef.current.onclose = (event) => {
        setIsConnected(false);
        setConnectionState('disconnected');

        if (event.code !== 1000) { // Not a normal closure
          attemptReconnect();
        }
      };

      wsRef.current.onerror = (event) => {
        setConnectionState('error');
        setError('WebSocket connection error');
        console.error('WebSocket error:', event);
      };

    } catch (err) {
      setError('Failed to create WebSocket connection');
      setConnectionState('error');
    }
  }, [url, tokens?.access_token]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
    }
    
    setIsConnected(false);
    setConnectionState('disconnected');
  }, []);

  const attemptReconnect = useCallback(() => {
    if (reconnectCountRef.current >= reconnectAttempts) {
      setError('Max reconnection attempts reached');
      return;
    }

    reconnectCountRef.current++;
    setConnectionState('connecting');

    reconnectTimeoutRef.current = setTimeout(() => {
      connect();
    }, reconnectInterval);
  }, [connect, reconnectAttempts, reconnectInterval]);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    const messageStr = JSON.stringify(message);

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(messageStr);
    } else {
      // Queue message for when connection is established
      messageQueueRef.current.push(messageStr);
    }
  }, []);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    // Handle specific message types
    switch (message.type) {
      case 'quote_update':
        if (message.symbol && message.data) {
          updateQuote(message.symbol, {
            symbol: message.symbol,
            price: message.data.price,
            bid: message.data.bid,
            ask: message.data.ask,
            volume: message.data.volume,
            change: message.data.change,
            change_percent: message.data.change_percent,
            market_status: message.data.market_status,
            timestamp: message.data.timestamp,
          });
        }
        break;
      
      case 'error':
        console.error('WebSocket error:', message.data);
        setError(message.data?.message || 'Unknown error');
        break;
      
      case 'connection_established':
        console.log('WebSocket connection established');
        break;
    }

    // Call registered handlers
    const handler = messageHandlers.current.get(message.type);
    if (handler) {
      handler(message.data);
    }
  }, [updateQuote]);

  const subscribe = useCallback((channel: string, symbols?: string[]) => {
    sendMessage({
      type: 'subscribe',
      data: { channel, symbols }
    });
  }, [sendMessage]);

  const unsubscribe = useCallback((channel: string) => {
    sendMessage({
      type: 'unsubscribe',
      data: { channel }
    });
  }, [sendMessage]);

  const subscribeToSymbols = useCallback((symbols: string[]) => {
    sendMessage({
      type: 'subscribe',
      data: { symbols }
    });
  }, [sendMessage]);

  const unsubscribeFromSymbols = useCallback((symbols: string[]) => {
    sendMessage({
      type: 'unsubscribe',
      data: { symbols }
    });
  }, [sendMessage]);

  const ping = useCallback(() => {
    sendMessage({
      type: 'ping',
      data: { timestamp: Date.now() }
    });
  }, [sendMessage]);

  const registerMessageHandler = useCallback((messageType: string, handler: (data: any) => void) => {
    messageHandlers.current.set(messageType, handler);
  }, []);

  const unregisterMessageHandler = useCallback((messageType: string) => {
    messageHandlers.current.delete(messageType);
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [connect, disconnect, autoConnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return {
    isConnected,
    connectionState,
    error,
    connect,
    disconnect,
    sendMessage,
    subscribe,
    unsubscribe,
    subscribeToSymbols,
    unsubscribeFromSymbols,
    ping,
    registerMessageHandler,
    unregisterMessageHandler,
  };
};