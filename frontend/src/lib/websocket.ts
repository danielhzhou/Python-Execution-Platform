import type { WebSocketMessage } from '../types';

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private containerId: string | null = null;
  private eventHandlers: Map<string, (message: WebSocketMessage) => void> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval: NodeJS.Timeout | null = null;

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get currentContainerId(): string | null {
    return this.containerId;
  }

  on(event: string, handler: (message: WebSocketMessage) => void): void {
    this.eventHandlers.set(event, handler);
  }

  off(event: string): void {
    this.eventHandlers.delete(event);
  }

  async connect(containerId: string): Promise<void> {
    this.containerId = containerId;
    
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = `ws://localhost:8000/api/ws/terminal/${containerId}`;
        console.log('🔌 Connecting to WebSocket:', wsUrl);
        
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('✅ WebSocket connected');
          this.reconnectAttempts = 0;
          this.startPing();
          
          const handler = this.eventHandlers.get('connection');
          if (handler) {
            handler({ type: 'connection', data: 'Connected' });
          }
          
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            console.log('📨 WebSocket message:', message);
            
            const handler = this.eventHandlers.get(message.type);
            if (handler) {
              handler(message);
            }
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.ws.onclose = (event) => {
          console.log('🔌 WebSocket closed:', event.code, event.reason);
          this.stopPing();
          
          const handler = this.eventHandlers.get('disconnection');
          if (handler) {
            handler({ type: 'disconnection', data: 'Disconnected' });
          }

          // Attempt reconnection if not intentionally closed
          if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.attemptReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error('❌ WebSocket error:', error);
          
          const handler = this.eventHandlers.get('error');
          if (handler) {
            handler({ 
              type: 'error', 
              message: 'WebSocket connection error',
              data: { message: 'Connection failed' }
            });
          }
          
          reject(new Error('WebSocket connection failed'));
        };

        // Timeout for connection
        setTimeout(() => {
          if (this.ws?.readyState !== WebSocket.OPEN) {
            reject(new Error('WebSocket connection timeout'));
          }
        }, 10000);

      } catch (error) {
        reject(error);
      }
    });
  }

  private attemptReconnect(): void {
    this.reconnectAttempts++;
    console.log(`🔄 Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts}...`);
    
    // Exponential backoff with jitter
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);
    const jitter = Math.random() * 1000; // Add up to 1 second of jitter
    
    setTimeout(() => {
      if (this.containerId) {
        this.connect(this.containerId).catch(error => {
          console.error('Reconnection failed:', error);
          
          // If we've exhausted all attempts, notify the user
          if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            const handler = this.eventHandlers.get('error');
            if (handler) {
              handler({ 
                type: 'error', 
                message: 'Failed to establish stable connection after multiple attempts',
                data: { message: 'Connection failed permanently' }
              });
            }
          }
        });
      }
    }, delay + jitter);
  }

  private startPing(): void {
    this.pingInterval = setInterval(() => {
      if (this.isConnected) {
        this.send({ type: 'ping' });
      }
    }, 30000); // Ping every 30 seconds
  }

  private stopPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  send(message: WebSocketMessage): void {
    if (this.isConnected && this.ws) {
      try {
        const messageStr = JSON.stringify(message);
        console.log('📤 Sending WebSocket message:', message);
        this.ws.send(messageStr);
      } catch (error) {
        console.error('Failed to send WebSocket message:', error);
      }
    } else {
      console.warn('WebSocket not connected, cannot send message:', message);
    }
  }

  disconnect(): void {
    this.stopPing();
    
    if (this.ws) {
      this.ws.close(1000, 'Intentional disconnect');
      this.ws = null;
    }
    
    // Clear all event handlers to prevent memory leaks and duplicate handlers
    this.eventHandlers.clear();
    
    this.containerId = null;
    this.reconnectAttempts = 0;
  }
}
