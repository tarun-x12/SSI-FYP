import websocket
import json
import threading
import time
import ssl

class CloudAgentClient:
    def __init__(self, my_did, message_callback=None):
        # Live Cloudflare Relay
        self.url = "wss://ssi-cloud-relay.becse2026fypp1-tno-20.workers.dev"
        
        self.did = my_did
        self.callback = message_callback
        self.ws = None
        self.is_connected = False
        self.incoming_buffer = []
        self.lock = threading.Lock()
        
        # STOP FLAG for background threads
        self.running = True

    def on_open(self, ws):
        print(f"[{self.did}] ☁️  Connected to Cloud Relay.")
        self.is_connected = True
        # Initial Register
        self.register()

    def register(self):
        """Sends a registration message to the cloud."""
        try:
            reg_msg = {"type": "register", "did": self.did}
            self.ws.send(json.dumps(reg_msg))
            # Optional: Print only if debugging
            # print(f"[{self.did}] 🔄 Refreshed Registration") 
        except Exception as e:
            print(f"[{self.did}] ⚠️ Registration Failed: {e}")

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if self.callback:
                self.callback(data)
            else:
                self.incoming_buffer.append(data)
        except Exception as e:
            print(f"[{self.did}] ⚠️ Error parsing msg: {e}")

    def on_error(self, ws, error):
        if "timed out" not in str(error) and "Connection to remote host" not in str(error):
             print(f"[{self.did}] ⚠️ Socket Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        self.is_connected = False

    def _keep_alive_loop(self):
        """
        CRITICAL FIX: Periodically Re-Registers.
        This prevents the Cloudflare Worker from 'forgetting' us 
        if the worker instance resets/recycles.
        """
        while self.running:
            if self.is_connected and self.ws:
                self.register()
            time.sleep(15) # Re-register every 15 seconds

    def connect(self):
        if self.is_connected:
            return

        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # 1. Start the WebSocket Loop
        t_ws = threading.Thread(
            target=self.ws.run_forever, 
            kwargs={"ping_interval": 10, "ping_timeout": 5, "sslopt": {"cert_reqs": ssl.CERT_NONE}}
        )
        t_ws.daemon = True
        t_ws.start()

        # 2. Start the Application-Level Keep-Alive Loop
        t_ka = threading.Thread(target=self._keep_alive_loop)
        t_ka.daemon = True
        t_ka.start()
        
        # Wait for connection
        retries = 0
        while not self.is_connected and retries < 10:
            time.sleep(0.5)
            retries += 1
        
        if self.is_connected:
            print(f"[{self.did}] ✅ Ready for Secure Messaging.")
        else:
            print(f"[{self.did}] ⚠️ Connection Unstable. Will retry automatically.")

    def send(self, target_did, msg_type, payload):
        """Robust Send with Retry"""
        msg = {
            "type": msg_type,
            "from": self.did,
            "to": target_did,
            "payload": payload
        }
        json_msg = json.dumps(msg)

        with self.lock:
            attempts = 0
            while attempts < 3:
                try:
                    if not self.is_connected:
                        raise Exception("Not connected")
                    
                    self.ws.send(json_msg)
                    print(f"[{self.did}] 📤 Sent {msg_type} to {target_did}")
                    return 
                
                except Exception as e:
                    print(f"[{self.did}] ⚠️ Send Failed ({e}). Reconnecting...")
                    self.is_connected = False
                    # Force a quick reconnect attempt
                    try:
                        self.ws.close()
                    except:
                        pass
                    self.connect()
                    attempts += 1
                    time.sleep(1)
            
            print(f"[{self.did}] ❌ Final Send Error: Could not deliver to {target_did}")