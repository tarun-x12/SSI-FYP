import websocket
import json
import threading
import time

class CloudAgentClient:
    def __init__(self, my_did, message_callback=None):
        # ✅ YOUR LIVE CLOUDFLARE URL (Converted to WSS)
        self.url = "wss://ssi-cloud-relay.becse2026fypp1-tno-20.workers.dev"
        
        self.did = my_did
        self.callback = message_callback
        self.ws = None
        self.is_connected = False
        self.incoming_buffer = []

    def on_open(self, ws):
        print(f"[{self.did}] ☁️  Connected to Cloud Relay. Registering...")
        # Register immediately so the relay knows where to route messages
        reg_msg = {"type": "register", "did": self.did}
        ws.send(json.dumps(reg_msg))
        self.is_connected = True

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            # If the main script provided a callback function, use it
            if self.callback:
                self.callback(data)
            else:
                self.incoming_buffer.append(data)
        except Exception as e:
            print(f"[{self.did}] ⚠️ Error parsing msg: {e}")

    def on_error(self, ws, error):
        print(f"[{self.did}] ⚠️ Socket Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        self.is_connected = False
        print(f"[{self.did}] 🔌 Disconnected.")

    def connect(self):
        """Starts the WebSocket connection in a background thread."""
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Run in a daemon thread so it doesn't block the ML training
        t = threading.Thread(target=self.ws.run_forever)
        t.daemon = True
        t.start()
        
        # Block briefly until connected
        retries = 0
        print(f"[{self.did}] Connecting to Cloud...")
        while not self.is_connected and retries < 10:
            time.sleep(0.5)
            retries += 1
        
        if self.is_connected:
            print(f"[{self.did}] ✅ Ready for Secure Messaging.")
        else:
            print(f"[{self.did}] ❌ Connection Timed Out.")

    def send(self, target_did, msg_type, payload):
        """Sends a structured message (M1/M2) to another DID."""
        if not self.is_connected:
            print("❌ Cannot send: Not connected.")
            return

        msg = {
            "type": msg_type,
            "from": self.did,
            "to": target_did,
            "payload": payload
        }
        self.ws.send(json.dumps(msg))
        print(f"[{self.did}] 📤 Sent {msg_type} to {target_did}")