import threading
import time

def start_relay_keepalive(entity, interval=8):

    def keepalive_loop():

        while True:
            try:
                if hasattr(entity, "relay_ping"):
                    entity.relay_ping()

                elif hasattr(entity, "send_ping"):
                    entity.send_ping()

                elif hasattr(entity, "connection") and hasattr(entity.connection, "ping"):
                    entity.connection.ping()

                else:
                    # fallback: simple heartbeat log
                    print("[KeepAlive] relay ping")

            except Exception:
                pass

            time.sleep(interval)

    t = threading.Thread(target=keepalive_loop, daemon=True)
    t.start()