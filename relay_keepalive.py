import threading
import time

def start_relay_keepalive(entity, interval=20):

    def keepalive_loop():

        while True:
            try:

                # only ping if connection exists
                if hasattr(entity, "connection") and entity.connection:

                    if hasattr(entity.connection, "ping"):
                        entity.connection.ping()

                    elif hasattr(entity, "relay_ping"):
                        entity.relay_ping()

                    elif hasattr(entity, "send_ping"):
                        entity.send_ping()

                # no connection → do nothing (prevents spam)

            except Exception:
                pass

            time.sleep(interval)

    t = threading.Thread(target=keepalive_loop, daemon=True)
    t.start()