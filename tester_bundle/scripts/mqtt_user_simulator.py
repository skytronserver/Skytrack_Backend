#!/usr/bin/env python3
import argparse
import json
import os
import random
import ssl
import string
import sys
import threading
import time

import paho.mqtt.client as mqtt


"""
python3 scripts/mqtt_user_simulator.py sosEx \
  --token "<JWT_TOKEN>" \
  --em-lat 26.157 --em-lon 91.757 --speed 12 \
  --host 135.235.166.209 --port 8883 \
  --cafile /home/azureuser/Skytrack_Backend/Skytronsystem/keys/ca.crt \
  --username "<MQTT_USERNAME>" --password "<MQTT_PASSWORD>" \
  --timeout 12









python3 scripts/mqtt_user_simulator.py owner \
  --token "<JWT_TOKEN>" \
  --host 135.235.166.209 --port 8883 \
  --cafile /home/azureuser/Skytrack_Backend/Skytronsystem/keys/ca.crt \
  --username "<MQTT_USERNAME>" --password "<MQTT_PASSWORD>" \
  --timeout 8
  
  
  
  
  
python3 scripts/mqtt_user_simulator.py dtorto \
  --token "<JWT_TOKEN>" \
  --host 135.235.166.209 --port 8883 \
  --cafile /home/azureuser/Skytrack_Backend/Skytronsystem/keys/ca.crt \
  --username "<MQTT_USERNAME>" --password "<MQTT_PASSWORD>" \
  --timeout 8
  
  
  

"""









def rand_id(n: int = 6) -> str:
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))


class MQTTSimulator:
    def __init__(self, host: str, port: int, cafile: str | None, insecure: bool,
                 username: str | None, password: str | None, timeout: float):
        self.host = host
        self.port = port
        self.cafile = cafile
        self.insecure = insecure
        self.username = username
        self.password = password
        self.timeout = timeout
        self.client = mqtt.Client()
        if username is not None:
            self.client.username_pw_set(username, password or "")

        # TLS setup (8883 typically requires TLS)
        if cafile:
            self.client.tls_set(ca_certs=cafile, certfile=None, keyfile=None,
                                 cert_reqs=ssl.CERT_REQUIRED,
                                 tls_version=ssl.PROTOCOL_TLSv1_2,
                                 ciphers=None)
        else:
            # Allow connecting without CA file if explicitly insecure or broker trusts system store
            self.client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
        if insecure:
            # Disable certificate hostname verification (only if user requests)
            self.client.tls_insecure_set(True)

        self._connected = threading.Event()
        self._got_final = threading.Event()
        self._messages: list[tuple[str, str]] = []

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected.set()
        else:
            print(f"[sim] Connect failed rc={rc}", flush=True)

    def _on_disconnect(self, client, userdata, rc):
        pass

    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode(errors='replace')
        self._messages.append((msg.topic, payload))
        # Heuristic: consider "status":"success" as final for sosEx; owner/dtorto likely single response
        try:
            data = json.loads(payload)
            if isinstance(data, dict) and data.get("status") == "success":
                self._got_final.set()
        except Exception:
            # Non-JSON or intermediate update; keep waiting until timeout
            pass

    def connect(self):
        self.client.connect(self.host, self.port, keepalive=60)
        self.client.loop_start()
        if not self._connected.wait(timeout=8):
            raise RuntimeError("Could not connect to MQTT broker in time")

    def close(self):
        try:
            self.client.loop_stop()
        finally:
            self.client.disconnect()

    def _wait_for_response(self):
        # Wait either until we have a final message or timeout
        end = time.time() + self.timeout
        while time.time() < end:
            if self._got_final.is_set():
                break
            time.sleep(0.05)

    def run_sos_ex(self, token: str, em_lat: float, em_lon: float, speed: float,
                   assignment_id: int | None):
        # Topics from server: publish to 'sosEx/<token>' and receive on 'sosEx/<token>/server'
        request_topic = f"sosEx/{token}"
        response_topic = f"sosEx/{token}/server"

        self.client.subscribe(response_topic)

        payload = {
            # Note: server reads token from topic, not body
            "em_lat": em_lat,
            "em_lon": em_lon,
            "speed": speed,
        }
        if assignment_id is not None:
            payload["assignment_id"] = assignment_id

        self.client.publish(request_topic, json.dumps(payload), qos=1)

        self._wait_for_response()
        return list(self._messages)

    def run_owner_or_dtorto(self, user_type: str, token: str, channel: str):
        # Topics from server: publish to '<user_type>/<channel>' and receive on same topic
        request_topic = f"{user_type}/{channel}"
        response_topic = request_topic  # server replies to the same topic

        self.client.subscribe(response_topic)

        payload = {
            "token": token
        }

        self.client.publish(request_topic, json.dumps(payload), qos=1)

        self._wait_for_response()
        return list(self._messages)


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="MQTT user simulator for sosEx, owner, dtorto"
    )
    parser.add_argument("mode", choices=["sosEx", "owner", "dtorto"], help="User type to simulate")

    # Broker
    parser.add_argument("--host", default=os.getenv("MQTT_BROKER_HOST", ""), help="MQTT broker host")
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_BROKER_PORT", "8883")), help="MQTT broker port")
    parser.add_argument("--cafile", default=os.getenv("MQTT_CAFILE", "/home/azureuser/Skytrack_Backend/Skytronsystem/keys/ca.crt"), help="Path to root CA file (PEM). If empty, system store is used.")
    parser.add_argument("--insecure", action="store_true", help="Disable TLS hostname verification (testing only)")

    # Auth
    parser.add_argument("--mqtt-username", default=os.getenv("MQTT_USERNAME"), help="MQTT username (preferred)")
    parser.add_argument("--jwt-token", default=os.getenv("JWT_TOKEN"), help="JWT token; also used as MQTT password by default")
    # Legacy/back-compat
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME") , help="MQTT username (legacy)")
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD"), help="MQTT password (legacy)")

    # General
    parser.add_argument("--timeout", type=float, default=8.0, help="Seconds to wait for responses")

    # sosEx specific
    parser.add_argument("--token", help="JWT token for sosEx (placed in topic) and for owner/dtorto (in payload)")
    parser.add_argument("--em-lat", type=float, default=26.157, help="em_lat for sosEx")
    parser.add_argument("--em-lon", type=float, default=91.757, help="em_lon for sosEx")
    parser.add_argument("--speed", type=float, default=12.0, help="speed for sosEx")
    parser.add_argument("--assignment-id", type=int, default=None, help="Optional assignment_id for sosEx")

    # owner/dtorto specific
    parser.add_argument("--channel", default=None, help="Second topic segment for owner/dtorto. Defaults to random.")

    args = parser.parse_args(argv)

    # Sanity checks per mode (prefer --jwt-token, fallback to --token)
    effective_token = args.jwt_token or args.token
    if args.mode == "sosEx" and not effective_token:
        parser.error("--jwt-token is required for sosEx (goes in topic)")
    if args.mode in ("owner", "dtorto") and not effective_token:
        parser.error("--jwt-token is required for owner/dtorto (goes in payload)")

    return args


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    args = parse_args(argv)

    cafile = args.cafile if args.cafile else None

    # Normalize credentials
    jwt_token = args.jwt_token or args.token
    mqtt_username = args.mqtt_username or args.username
    mqtt_password = jwt_token or args.password

    sim = MQTTSimulator(
        host=args.host,
        port=args.port,
        cafile=cafile,
        insecure=args.insecure,
        username=mqtt_username,
        password=mqtt_password,
        timeout=args.timeout,
    )

    try:
        sim.connect()
        if args.mode == "sosEx":
            messages = sim.run_sos_ex(
                token=jwt_token,
                em_lat=args.__dict__["em_lat"],
                em_lon=args.__dict__["em_lon"],
                speed=args.speed,
                assignment_id=args.assignment_id,
            )
        else:
            # Default channel equals token unless explicitly provided
            channel = args.channel or jwt_token
            messages = sim.run_owner_or_dtorto(
                user_type=args.mode,
                token=jwt_token,
                channel=channel,
            )

        if not messages:
            print("[sim] No response messages received (timed out).", flush=True)
        else:
            print("[sim] Responses:")
            for topic, payload in messages:
                print(f"  topic={topic}")
                try:
                    data = json.loads(payload)
                    print(json.dumps(data, indent=2))
                except Exception:
                    print(payload)

    except Exception as e:
        print(f"[sim] Error: {e}")
        sys.exit(1)
    finally:
        try:
            sim.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
