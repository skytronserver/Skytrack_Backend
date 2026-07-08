#!/usr/bin/env python3
import os
import json
import sys
from mqtt_user_simulator import MQTTSimulator

# Fill these or set env vars USER_ID and JWT_TOKEN
USER_ID = os.getenv("USER_ID", "")
JWT_TOKEN = os.getenv("JWT_TOKEN", "")

# Optional overrides via env
HOST = os.getenv("MQTT_HOST", "")
PORT = int(os.getenv("MQTT_PORT", "8883"))
CAFILE = os.getenv("MQTT_CAFILE", "/home/azureuser/Skytrack_Backend/Skytronsystem/keys/ca.crt")
TIMEOUT = int(os.getenv("MQTT_TIMEOUT", "12"))
INSECURE = os.getenv("MQTT_INSECURE", "0").lower() in ("1", "true", "yes")

# sosEx payload defaults (override via env if needed)
EM_LAT = float(os.getenv("EM_LAT", "26.157"))
EM_LON = float(os.getenv("EM_LON", "91.757"))
SPEED = float(os.getenv("EM_SPEED", "12"))


def main():
    if not USER_ID or not JWT_TOKEN:
        print("ERROR: Set USER_ID and JWT_TOKEN (env or edit script).")
        raise SystemExit(1)

    sim = MQTTSimulator(
        host=HOST,
        port=PORT,
        cafile=CAFILE,
        insecure=INSECURE,
        username=USER_ID,
        password=JWT_TOKEN,
        timeout=TIMEOUT,
    )

    try:
        sim.connect()
        responses = sim.run_sos_ex(
            token=JWT_TOKEN,
            em_lat=EM_LAT,
            em_lon=EM_LON,
            speed=SPEED,
            assignment_id=None,
        )

        print("[sim_sosEx] Responses:")
        for topic, payload in responses:
            try:
                data = json.loads(payload)
                payload_str = json.dumps(data, ensure_ascii=False, indent=2)
            except Exception:
                payload_str = str(payload)
            try:
                print(f"  topic={topic}\n{payload_str}")
            except BrokenPipeError:
                # Downstream pipe (e.g., `head`) closed; exit cleanly
                try:
                    sys.stderr.close()
                except Exception:
                    pass
                raise SystemExit(0)
    finally:
        sim.close()


if __name__ == "__main__":
    main()
