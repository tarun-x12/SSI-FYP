import time
from ssi_utils import load_json
from cloud_client import CloudAgentClient


def run_replay_attack():

    print("\n" + "="*60)
    print("      ⚠ TEST CASE: REPLAY ATTACK")
    print("      (Reusing a previously captured model update)")
    print("="*60)

    # Load captured update
    try:
        captured = load_json("captured_update.json")
    except:
        print("❌ captured_update.json not found")
        print("Run one normal FL round first to capture an update")
        return

    sender_did = captured["sender_did"]
    payload = captured["payload"]

    print("[Attacker] Loaded captured update")
    print("[Attacker] Pretending to be:", sender_did)

    # Dummy callback
    def on_reply(msg):
        pass

    cloud = CloudAgentClient(sender_did, on_reply)

    cloud.connect()

    print("[Attacker] Sending replayed update to analyst")

    # Replay the old message
    cloud.send(payload["sender_did"], "M2", payload)

    print("[Attacker] Replay attack sent")

    time.sleep(3)


if __name__ == "__main__":

    run_replay_attack()