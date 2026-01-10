// src/index.js

// 1. The Main Worker Entry Point
export default {
  async fetch(request, env) {
    // Forward everything to a single Durable Object instance named "HUB"
    // This ensures all users connect to the SAME room and can find each other.
    const id = env.RELAY_HUB.idFromName("GLOBAL_HUB");
    const stub = env.RELAY_HUB.get(id);
    return stub.fetch(request);
  }
};

// 2. The Durable Object (The "Room" where connections live)
export class RelayHub {
  constructor(state, env) {
    this.state = state;
    // Map to store active connections: DID -> WebSocket
    this.sessions = new Map();
  }

  async fetch(request) {
    // Only allow WebSocket upgrades
    if (request.headers.get("Upgrade") !== "websocket") {
      return new Response("Expected WebSocket", { status: 426 });
    }

    // Accept the connection
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    
    // We must accept the server side
    this.handleSession(server);

    return new Response(null, { status: 101, webSocket: client });
  }

  handleSession(webSocket) {
    webSocket.accept();
    let myDID = null;

    webSocket.addEventListener("message", async (msg) => {
      try {
        const data = JSON.parse(msg.data);

        // CASE 1: Registration (User says "I am DID X")
        if (data.type === "register") {
          myDID = data.did;
          this.sessions.set(myDID, webSocket);
          console.log(`[Cloud] Registered: ${myDID}`);
          return;
        }

        // CASE 2: Message Relay (User sends M1/M2)
        if (data.to && data.payload) {
          const targetSocket = this.sessions.get(data.to);
          
          if (targetSocket && targetSocket.readyState === 1) { // 1 = OPEN
            // Forward the message exactly as is
            targetSocket.send(JSON.stringify(data));
            console.log(`[Cloud] Relayed ${data.type} from ${data.from} to ${data.to}`);
          } else {
            console.log(`[Cloud] Drop: Target ${data.to} not connected.`);
            // Optional: Send error back to sender
          }
        }
      } catch (err) {
        console.error("[Cloud] Error parsing message:", err);
      }
    });

    // Clean up on disconnect
    webSocket.addEventListener("close", () => {
      if (myDID) {
        this.sessions.delete(myDID);
        console.log(`[Cloud] Disconnected: ${myDID}`);
      }
    });
  }
}