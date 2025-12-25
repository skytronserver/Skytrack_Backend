#!/usr/bin/env python3
import os
import ssl
import sys
import time
import argparse
from datetime import datetime

import paho.mqtt.client as mqtt


def build_client(client_id: str,
                 host: str,
                 port: int,
                 username: str,
                 password: str,
                 ca_file: str,
                 keepalive: int = 60) -> mqtt.Client:
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    if username:
        client.username_pw_set(username, password)

    # TLS settings
    client.tls_set(ca_certs=ca_file, certfile=None, keyfile=None,
                   tls_version=ssl.PROTOCOL_TLSv1_2)
    client.tls_insecure_set(False)

    def on_connect(c, userdata, flags, rc):
        status = mqtt.error_string(rc)
        print(f"[connect] rc={rc} ({status}) at {datetime.utcnow().isoformat()}Z")

    def on_subscribe(c, userdata, mid, granted_qos):
        print(f"[subscribed] mid={mid}, qos={granted_qos}")

    def on_message(c, userdata, msg):
        now = datetime.utcnow().isoformat() + "Z"
        try:
            payload = msg.payload.decode('utf-8', errors='replace')
        except Exception:
            payload = str(msg.payload)
        print(f"[msg] {now} topic={msg.topic} qos={msg.qos} retain={msg.retain} payload={payload}")

    def on_disconnect(c, userdata, rc):
        print(f"[disconnect] rc={rc} ({mqtt.error_string(rc)})")

    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    client.connect(host, port, keepalive=keepalive)
    return client


def main():
    parser = argparse.ArgumentParser(description="Subscribe to a topic using TLS and username/password")
    parser.add_argument("topic", help="MQTT topic to subscribe to (exact string)")
    parser.add_argument("--host", default=os.getenv("MQTT_BROKER_HOST", "localhost"), help="MQTT broker host")
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_BROKER_PORT", "8883")), help="MQTT broker port")
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME", os.getenv("MQTT_ADMIN_USER", "admin")), help="MQTT username")
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD", os.getenv("MQTT_ADMIN_PASS", "adminpass")), help="MQTT password")
    parser.add_argument("--cafile", default=os.getenv("MQTT_CA_FILE", "/etc/mosquitto/certs/ca_chain.crt"), help="Path to CA certificate/chain file")
    parser.add_argument("--client-id", default=f"skytrack-sub-{int(time.time())}", help="MQTT client id")
    parser.add_argument("--qos", type=int, default=0, choices=[0, 1, 2], help="Subscription QoS")
    args = parser.parse_args()

    print("Using settings:")
    print(f"  host={args.host} port={args.port}")
    print(f"  username={args.username}")
    print(f"  cafile={args.cafile}")
    print(f"  topic={args.topic}")

    client = build_client(
        client_id=args.client_id,
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        ca_file=args.cafile,
    )

    client.loop_start()
    # Subscribe after connection establishes; a small delay avoids race on fast systems
    time.sleep(0.2)
    rc, mid = client.subscribe(args.topic, qos=args.qos)
    if rc != mqtt.MQTT_ERR_SUCCESS:
        print(f"Subscribe failed: rc={rc} ({mqtt.error_string(rc)})")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted, disconnecting...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    sys.exit(main())
