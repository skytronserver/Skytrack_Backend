# Standard library
import json
import os
import ssl
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Optional, Tuple

# Third-party
import django
import paho.mqtt.client as mqtt
from geopy.distance import geodesic
from rest_framework.exceptions import AuthenticationFailed

# Django setup must happen before any app imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Skytronsystem.settings")
django.setup()

# Django / local app
from django.utils import timezone
from skytron_api.data_processor import (
    extract_log_meta,
    get_device_response_data,
    process_device_tracking_data,
    process_emergency_data,
)
from skytron_api import connection_registry, mqtt_client_ip
from skytron_api.jwt_authentication import HybridAuthentication
from skytron_api.models import (  # noqa: F401 – wildcard kept for dynamic model access
    EMCallAssignment, EMCallBroadcast, EMCallMessages,
    EMUserLocation, GPSData, AlertsLog, DeviceTag, DeviceStock,
)
from skytron_api.serializers import (  # noqa: F401 – wildcard kept for dynamic serializer access
    EMCallBroadcastSerializer, EMCallMessagesSerializer, AlertsLogSerializer,
)
from skytron_api.views import get_user_object

# MQTT Settings - using environment variables for deployment flexibility
BROKER_URL = os.getenv("MQTT_BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "8883"))  # Use SSL/TLS port

# MQTT Authentication - using environment variables
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_CA = os.getenv(
    "MQTT_CA_CERT",
    os.path.join(_BASE_DIR, "keys", "ca.crt"),
)









 





authenticator = HybridAuthentication()


class FakeRequest:
    """Minimal request-like object for DRF authentication backends."""

    def __init__(self, auth_header: str) -> None:
        self.META = {'HTTP_AUTHORIZATION': auth_header}
        self.data = {}
        self.GET = {}


def authenticate_topic_user(token: str, topic_parts) -> Optional[Tuple[object, object]]:
    """Authenticate MQTT topic token and return DRF auth tuple or None."""
    auth_header = f"Token {token}"
    try:
        fake_request = FakeRequest(auth_header)
        user_auth_tuple = authenticator.authenticate(fake_request)
        if user_auth_tuple is None:
            raise AuthenticationFailed("Invalid token.")
        return user_auth_tuple
    except AuthenticationFailed as e:
        error_message = f"Authentication mqtt error: {topic_parts[0]} {topic_parts[1]} {str(e)}"
        print(error_message)
        return None



# Callback when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully")
        topics = [
            ("deviceTracking/+", 0),
            ("deviceEM/+", 0),
            ("sosEx/#", 0),
            ("owner/+", 0),
            ("dtorto/+", 0),
        ]
        client.subscribe(topics)
    else:
        print(f"Connection failed with code {rc}")


# Lightweight execution time logger
def log_exec_time(name, func, *args, **kwargs):
    start = time.perf_counter()
    try:
        return func(*args, **kwargs)
    finally:
        duration_ms = (time.perf_counter() - start) * 1000.0
        print(f"[MQTT][Perf] {name} took {duration_ms:.2f} ms", flush=True)


def Process_sosEx_Data(msg, topic_parts):
    """Handle sosEx/<token> updates and publish executive-facing responses."""
    try:
        raw_message = msg.payload.decode()
        if len(topic_parts) > 2:
            #print(f"Topic parts: {topic_parts}")    
            #print(f"Raw message received: {raw_message}")
            return 0
        
        try:
            data = json.loads(raw_message)
            
        except json.JSONDecodeError as je:
            print(f"JSON Decode Error: {je}")
            #print(f"Raw message that failed: '{raw_message}'")
            client.publish(topic_parts[0]+"/"+topic_parts[1]+"/server", json.dumps({"status": "error", "message": f"Invalid JSON format: {str(je)}"}))
            return
            
        print("Parsed data:", data)

        token = topic_parts[1]  # token is the second part of the topic path
        if token:
            client.publish(topic_parts[0]+"/"+topic_parts[1]+"/server", json.dumps({"status": "update", "message": "user authentication in progress"}))

            user_auth_tuple = authenticate_topic_user(token, topic_parts)
            if user_auth_tuple is None:
                return

            client.publish(topic_parts[0]+"/"+topic_parts[1]+"/server", json.dumps({"status":"update", "message": "user found"}))
            user = user_auth_tuple[0]  # Extract the user from the authentication tuple

            # Get user object and validate roles
            role = "sosexecutive"
            uo = get_user_object(user, role)

            if not uo:
                error_message = f"Request must be from {role}"
                print(error_message)
                client.publish(topic_parts[0]+"/"+topic_parts[1]+"/server", json.dumps({"status": "error", "message": error_message}))
                return

            try:
                em_lat = float(data.get("em_lat"))
                em_lon = float(data.get("em_lon"))
                speed = float(data.get("speed"))
                print("em_lat, em_lon, speed:", em_lat, em_lon, speed)
            except (TypeError, ValueError) as ve:
                error_message = f"Invalid location or speed data: {ve}"
                print(error_message)
                client.publish(topic_parts[0]+"/"+topic_parts[1]+"/server", json.dumps({"status": "error", "message": error_message}))
                return
            except Exception as e:
                error_message = f"Error processing location or speed data: {e}"
                print(error_message)
                client.publish(topic_parts[0]+"/"+topic_parts[1]+"/server", json.dumps({"status": "error", "message": error_message}))
                return

            EMUserLocation.objects.create(field_ex=uo, em_lat=em_lat, em_lon=em_lon, speed=speed)
            user.last_activity = timezone.now()
            user.login = True
            user.save()
            success_message = "Location updated successfully"
            assignment_id = data.get("assignment_id")
            print(f"assignmentid:{assignment_id}")

            if assignment_id is not None:
                try:
                    assignment = EMCallAssignment.objects.filter(id=assignment_id, ex=uo, status__in=["accepted"], call__status="pending").last()
                    if not assignment:
                        client.publish(topic_parts[0]+"/"+topic_parts[1]+"/server", json.dumps({"status": "error", "message": "Invalid assignment id"}))
                        return

                    ee = EMCallBroadcast.objects.filter(type=uo.user_type, call=assignment.call, status="accepted", call__status="pending").order_by('-id')[:1]
                    msg2 = EMCallMessages.objects.filter(call=assignment.call).all()

                    data_to_send = {"status": "success", "broadcast": EMCallBroadcastSerializer(ee, many=True).data, "groupMSG": EMCallMessagesSerializer(msg2, many=True).data, "message": success_message}
                    client.publish(topic_parts[0]+"/"+topic_parts[1]+"/server", json.dumps(data_to_send))

                    lat = None
                    lon = None
                    try:
                        b = data_to_send.get("broadcast") or []
                        if b:
                            dloc = b[0].get("call", {}).get("device", {}).get("deviceloc") or []
                            if dloc:
                                lat = dloc[0].get("latitude")
                                lon = dloc[0].get("longitude")
                    except Exception:
                        pass

                    print("sending accepted call data ----", "UserObject:", uo, "pendning broadcast list :", ee, "first_device_lat_lon:", lat, lon)
                    return
                except Exception as e:
                    print(f"assignmentid error: {assignment_id}")
                    client.publish(topic_parts[0]+"/"+topic_parts[1]+"/server", json.dumps({"status": "update", "logseq": "2", "message": str(e)}))
                    return

            # No assignment_id — send pending broadcasts within 10 km of this executive.
            PROXIMITY_KM = 10.0
            candidate_qs = EMCallBroadcast.objects.filter(
                type=uo.user_type, status="pending"
            ).select_related("call__device").order_by('-id')[:50]

            ee_list = []
            for bc in candidate_qs:
                try:
                    gps = GPSData.objects.filter(
                        device_tag=bc.call.device, gps_status='1'
                    ).order_by('-id').values('latitude', 'longitude').first()
                    if gps and gps['latitude'] and gps['longitude']:
                        dist_km = geodesic((em_lat, em_lon), (gps['latitude'], gps['longitude'])).km
                        if dist_km <= PROXIMITY_KM:
                            ee_list.append(bc)
                except Exception as _dist_err:
                    print(f"[sosEx] distance filter error for broadcast {bc.id}: {_dist_err}", flush=True)

            if ee_list:
                dat = {"status": "success", "broadcast": EMCallBroadcastSerializer(ee_list, many=True).data, "message": success_message}
            else:
                dat = {"status": "success", "broadcast": [], "message": success_message}
            client.publish(topic_parts[0]+"/"+topic_parts[1]+"/server", json.dumps(dat))
            print("sending pending broadcast list----", "UserObject:", uo, "pending broadcast list:", ee_list)
            return

        else:
            print("Invalid token in message payload")

    except Exception as e:
        client.publish(topic_parts[0]+"/"+topic_parts[1]+"/server", json.dumps({"status": "error", "message": "Something went wrong."}))
        print("[sosEx] data processing error:", e)
        raise e


def Process_owner_Data(msg, topic_parts):
    """Handle owner/<token> requests and publish alert history."""
    try:
        data = json.loads(msg.payload.decode())
        token = data.get("token")

        if token:
            user_auth_tuple = authenticate_topic_user(token, topic_parts)
            if user_auth_tuple is None:
                return

            user = user_auth_tuple[0]
            role = "owner"
            uo = get_user_object(user, role)

            response_topic = topic_parts[0]+"/"+topic_parts[1]+"/server"

            if not uo:
                error_message = f"Request must be from {role}"
                print(error_message)
                client.publish(response_topic, json.dumps({"status": "error", "message": error_message}))
                return

            user.last_activity = timezone.now()
            user.login = True
            user.save()

            try:
                from skytron_api.models import VehicleOwner
                vehicle_owners = VehicleOwner.objects.filter(users=user)
                alerts = AlertsLog.objects.filter(
                    deviceTag__vehicle_owner__in=vehicle_owners
                ).select_related('gps_ref', 'deviceTag').order_by('-id')[:10]
                alert_list = []
                for a in alerts:
                    try:
                        gps = a.gps_ref
                        tag = a.deviceTag
                        alert_list.append({
                            "id": a.id,
                            "type": a.type,
                            "status": a.status,
                            "timestamp": str(a.timestamp),
                            "alert_details": a.alert_details,
                            "vehicle_reg_no": getattr(tag, 'vehicle_reg_no', ''),
                            "device_tag_id": tag.id,
                            "latitude": str(gps.latitude) if gps else None,
                            "longitude": str(gps.longitude) if gps else None,
                            "speed": str(gps.speed) if gps else None,
                        })
                    except Exception:
                        pass
                client.publish(response_topic, json.dumps({"status": "success", "alertHistory": alert_list}))
                print(f"data sent: {len(alert_list)} alerts")
            except Exception as e:
                print(f"[owner] alert query error: {e}")
                client.publish(response_topic, json.dumps({"status": "error", "message": "Failed to fetch alerts"}))

    except Exception as e:
        raise e


def Process_dtorto_Data(msg, topic_parts):
    """Handle dtorto/<token> requests and publish alert history."""
    try:
        data = json.loads(msg.payload.decode())
        token = data.get("token")

        if token:
            user_auth_tuple = authenticate_topic_user(token, topic_parts)
            if user_auth_tuple is None:
                return

            user = user_auth_tuple[0]
            role = "dtorto"
            uo = get_user_object(user, role)

            if not uo:
                error_message = f"Request must be from {role}"
                print(error_message)
                client.publish(topic_parts[0]+"/"+topic_parts[1]+"/server", json.dumps({"status": "error", "message": error_message}))
                return

            user.last_activity = timezone.now()
            user.login = True
            user.save()

            try:
                response_topic = topic_parts[0]+"/"+topic_parts[1]+"/server"
                alerts = AlertsLog.objects.order_by('-id')[:10]
                if alerts:
                    serializer = AlertsLogSerializer(alerts, many=True)
                    client.publish(response_topic, json.dumps({"status": "success", "alertHistory": serializer.data}))
                    print("data sent")
                else:
                    client.publish(response_topic, json.dumps({"status": "success", "alertHistory": []}))
                    print("no data")
            except Exception as e:
                print(e)

    except Exception as e:
        raise e


def _tracking_worker_init():
    """Runs once at startup in each tracking worker PROCESS.

    Workers are forked from the main process, which may already hold a live
    DB connection at fork time -- sharing that same socket across process
    boundaries corrupts the wire protocol. Discard it here so each worker
    opens its own fresh connection on its first query.
    """
    from django.db import connections
    connections.close_all()


def _process_tracking_message(payload, source_ip=None):
    """Process one deviceTracking message. Runs in a worker PROCESS (not a
    thread) so CPU-bound work (parsing, ORM hydration, alert evaluation)
    gets real multi-core parallelism instead of competing for one GIL.

    Returns (imei, response_data) instead of publishing directly -- worker
    processes don't hold the MQTT client connection, only the main process
    does. The main process publishes the response via a completion callback.
    """
    start = time.perf_counter()
    try:
        data_str = payload.decode()
        process_device_tracking_data(data_str, source="MQTT", source_ip=source_ip)

        # Extract IMEI for PVT format: $,PVT,<model>,<ver>,NR,<seq>,L,<imei>,...
        imei = None
        try:
            data_parts = data_str.split(',')
            if len(data_parts) > 7:
                imei = data_parts[7]
                connection_registry.record_mqtt_seen(imei, topic="deviceTracking/" + imei)
        except Exception as e:
            print(f"[MQTT] Error extracting IMEI: {e}", flush=True)

        if imei:
            response_data = get_device_response_data(imei)
            return imei, response_data
        return None

    except Exception as e:
        print(f"[MQTT] Device data processing error: {e}", flush=True)
        return None
    finally:
        duration_ms = (time.perf_counter() - start) * 1000.0
        print(f"[MQTT][Perf] Process_Device_Data took {duration_ms:.2f} ms", flush=True)


def _publish_tracking_response(future):
    """Runs in the main process when a tracking worker process completes.
    Only the main process holds the MQTT client, so the actual publish()
    has to happen here rather than inside the worker.
    """
    try:
        result = future.result()
    except Exception as e:
        print(f"[MQTT] tracking worker error: {e}", flush=True)
        return
    if result:
        imei, response_data = result
        try:
            client.publish(f"deviceResponse/{imei}", json.dumps(response_data))
        except Exception as e:
            print(f"[MQTT] Error sending device response: {e}", flush=True)


def Process_EM_Data(msg, source_ip=None):
    """Process emergency data using common processor."""
    data_str = str(msg.payload.decode())
    process_emergency_data(data_str, source="MQTT", publish_callback=client.publish, source_ip=source_ip)


def _device_source_ip(topic_parts, payload):
    """Device's public IP as reported from the broker VM (see mqtt_client_ip).
    Devices publish on <prefix>/<imei>; fall back to the IMEI in the payload."""
    ip = mqtt_client_ip.lookup(topic_parts[1])
    if ip is None:
        try:
            ip = mqtt_client_ip.lookup(extract_log_meta(payload.decode(errors='ignore'))[0])
        except Exception:
            ip = None
    return ip


def on_message(client, userdata, msg):
    """Route incoming MQTT messages to the appropriate handler.

    Priority design:
    - deviceEM / sosEx messages go to the HIGH-PRIORITY executor (max 4 workers)
      so SOS/emergency data is NEVER queued behind slow tracking packets.
    - deviceTracking / owner / dtorto go to the NORMAL executor (max 2 workers)
      to bound CPU usage from the geodesic route-checking loop.
    """
    try:
        topic_parts = msg.topic.split('/')

        # Ignore server-side reply topics to prevent processing loops
        if len(topic_parts) >= 3 and topic_parts[-1] in ("server", "response", "noLocal"):
            return

        if len(topic_parts) == 2 and topic_parts[0] == 'deviceTracking':
            future = _tracking_executor.submit(
                _process_tracking_message, msg.payload, _device_source_ip(topic_parts, msg.payload))
            future.add_done_callback(_publish_tracking_response)
        elif len(topic_parts) == 2 and topic_parts[0] == 'deviceEM':
            _em_executor.submit(_safe_exec, "Process_EM_Data", Process_EM_Data, msg,
                                _device_source_ip(topic_parts, msg.payload))
        elif len(topic_parts) >= 2 and topic_parts[0] == 'sosEx':
            _em_executor.submit(_safe_exec, "Process_sosEx_Data", Process_sosEx_Data, msg, topic_parts)
        elif len(topic_parts) == 2 and topic_parts[0] == 'owner':
            _user_executor.submit(_safe_exec, "Process_owner_Data", Process_owner_Data, msg, topic_parts)
        elif len(topic_parts) == 2 and topic_parts[0] == 'dtorto':
            _user_executor.submit(_safe_exec, "Process_dtorto_Data", Process_dtorto_Data, msg, topic_parts)
        elif len(topic_parts) == 2 and topic_parts[0] == 'deviceResponse':
            return  # responses are published by us; nothing to process
        else:
            print(f"[MQTT] Unknown topic format: {topic_parts}")

    except Exception as e:
        print(f"[MQTT] on_message error: {e}", flush=True)
        raise e


def _safe_exec(name, func, *args, **kwargs):
    """Wrapper executed inside a thread-pool worker: logs total time."""
    log_exec_time(name, func, *args, **kwargs)


# ---------------------------------------------------------------------------
# Executors
# EM/SOS messages → high-priority thread pool (never blocked by tracking).
# Device tracking → process pool, so CPU-bound work (parsing, ORM hydration,
#   alert evaluation) gets real multi-core parallelism instead of competing
#   for one GIL across 32 threads. Tunable via MQTT_TRACKING_WORKERS since
#   this shares the host with mosquitto, the API backend, and Postgres.
# Owner/dtorto → dedicated thread pool so user requests are never queued
#   behind slow device tracking tasks.
# ---------------------------------------------------------------------------
_em_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="mqtt-em")
_tracking_executor = ProcessPoolExecutor(
    max_workers=int(os.getenv("MQTT_TRACKING_WORKERS", "6")),
    initializer=_tracking_worker_init,
)
_user_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="mqtt-user")

# ---------------------------------------------------------------------------
# MQTT client setup
# ---------------------------------------------------------------------------
client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# TLS: certificate chain validation, hostname verification, no bypass
client.tls_set(
    ca_certs=ROOT_CA,
    certfile=None,
    keyfile=None,
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLSv1_2,
    ciphers=None,
)

client.on_connect = on_connect
client.on_message = on_message

# Connect and use loop_start() so the MQTT network thread is non-blocking.
# All heavy processing is dispatched to thread-pool executors in on_message.
client.connect(BROKER_URL, BROKER_PORT, 60)
client.loop_start()

print("[MQTT] Client started (tracking: process pool, EM/user: thread pools). Waiting for messages...", flush=True)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("[MQTT] Shutting down...", flush=True)
finally:
    client.loop_stop()
    client.disconnect()
    _em_executor.shutdown(wait=False)
    _tracking_executor.shutdown(wait=False)
    _user_executor.shutdown(wait=False)
