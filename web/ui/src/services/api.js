const API_BASE = ""; 

export const api = {
  get: async (endpoint) => {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`);
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      console.error("API GET Error:", e);
      return null;
    }
  },

  post: async (endpoint, body) => {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      console.error("API POST Error:", e);
      return null;
    }
  },

  delete: async (endpoint) => {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "DELETE",
      });
      return await res.json();
    } catch (e) {
      console.error("API DELETE Error:", e);
      return null;
    }
  }
};

class SocketManager {
  constructor() {
    this.ws = null;
    this.listeners = new Set();
    // Default URL construction
    this.url = (location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + location.host + '/ws';
  }

  connect() {
    try {
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) return;
        
        // Dev override
        if (location.port === "5173") {
          this.url = "ws://localhost:8080/ws";
        }
    
        this.ws = new WebSocket(this.url);
    
        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.listeners.forEach(cb => cb(data));
          } catch (e) {
            console.error("WS Parse Error", e);
          }
        };
    
        this.ws.onclose = () => {
          console.log("WS Closed, reconnecting...");
          setTimeout(() => this.connect(), 3000);
        };
    
        this.ws.onerror = (err) => {
          console.error("WS Error", err);
          try { this.ws.close(); } catch(e){}
        };
    } catch (e) {
        console.error("WS Connection Failed:", e);
    }
  }

  subscribe(callback) {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }
}

export const socket = new SocketManager();