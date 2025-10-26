/**
 * WebSocket Client for real-time bot updates
 */

type MessageHandler = (data: any) => void;
type ErrorHandler = (error: Event) => void;
type CloseHandler = () => void;

interface WebSocketMessage {
  type: string;
  timestamp: string;
  data: any;
}

class WebSocketClient {
  private ws: WebSocket | null = null;
  private botId: string | null = null;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectDelay: number = 1000;
  private messageHandlers: Set<MessageHandler> = new Set();
  private errorHandlers: Set<ErrorHandler> = new Set();
  private closeHandlers: Set<CloseHandler> = new Set();
  private shouldReconnect: boolean = true;

  /**
   * Connect to WebSocket server for a specific bot
   */
  connect(botId: string, onMessage: MessageHandler): void {
    this.botId = botId;
    this.messageHandlers.add(onMessage);
    this.shouldReconnect = true;
    this.reconnectAttempts = 0;

    this.createConnection();
  }

  /**
   * Create WebSocket connection
   */
  private createConnection(): void {
    if (!this.botId) {
      console.error('Cannot connect: no bot ID');
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/bots/${this.botId}/stream`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log(`WebSocket connected for bot ${this.botId}`);
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onerror = (error: Event) => {
        console.error('WebSocket error:', error);
        this.errorHandlers.forEach((handler) => handler(error));
      };

      this.ws.onclose = () => {
        console.log(`WebSocket closed for bot ${this.botId}`);
        this.closeHandlers.forEach((handler) => handler());

        // Attempt reconnection if needed
        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
          console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
          
          setTimeout(() => {
            if (this.shouldReconnect) {
              this.createConnection();
            }
          }, delay);
        }
      };
    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
    }
  }

  /**
   * Handle incoming message
   */
  private handleMessage(message: WebSocketMessage): void {
    this.messageHandlers.forEach((handler) => handler(message));
  }

  /**
   * Send message to server
   */
  send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnect(): void {
    this.shouldReconnect = false;
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.messageHandlers.clear();
    this.errorHandlers.clear();
    this.closeHandlers.clear();
    this.botId = null;
  }

  /**
   * Add error handler
   */
  onError(handler: ErrorHandler): void {
    this.errorHandlers.add(handler);
  }

  /**
   * Add close handler
   */
  onClose(handler: CloseHandler): void {
    this.closeHandlers.add(handler);
  }

  /**
   * Get connection state
   */
  get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Get current bot ID
   */
  get currentBotId(): string | null {
    return this.botId;
  }
}

// Export singleton instance
export const wsClient = new WebSocketClient();

// Export class for testing
export default WebSocketClient;