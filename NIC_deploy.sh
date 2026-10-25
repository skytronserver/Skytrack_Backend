#!/bin/bash
# NIC production (3 VMs): run on the control VM (10.192.136.175) with no arguments.
#   ./NIC_deploy.sh               git pull here, then deploy in this order, stopping at the
#                                 first failure so at least one API VM stays up:
#                                   1. shared Redis        on REDIS_HOST (run_redis.sh)
#                                   2. API + migrations    on this VM
#                                   3. API                 on NIC_API2_HOST
#                                   4. MQTT processor      on NIC_MQTT_HOST
#                                 Images are built only here and copied to the other VMs
#                                 (with this VM's code and .env minus the NIC_*_PASS lines)
#                                 over SSH, so every VM runs the identical image and needs
#                                 neither git nor package downloads.
#                                 Settings: the "NIC multi-VM" block in .env.
#                                 Without NIC_API2_HOST / NIC_MQTT_HOST in .env (dev, one VM)
#                                 it does the same as `backend`.
#
# Single roles (what the control VM runs on each VM; also usable by hand):
#   ./NIC_deploy.sh backend          one VM: API, migrations, MQTT client
#                                    (+ IP reporter if Mosquitto runs on this VM too)
#   ./NIC_deploy.sh api [--migrate]  API only
#   ./NIC_deploy.sh mqtt-processor   MQTT client only
#   ./NIC_deploy.sh redis            shared Redis only
#   ./NIC_deploy.sh mqtt-reporter    broker VM: only the MQTT IP reporter container.
#                                    First time: ./NIC_deploy.sh mqtt-reporter --key <MQTT_IP_REPORT_KEY>
#                                    (extra args go to run_mqtt_reporter.sh)
set -eE
cd "$(dirname "$0")"

ENV_FILE="${ENV_FILE:-.env}"
if [ ! -f "$ENV_FILE" ] && [ -f ".renv" ]; then
    ENV_FILE=".renv"
fi
[ -f "$ENV_FILE" ] && source "$ENV_FILE"

if [ $# -gt 0 ]; then
    ROLE="$1"; shift
elif [ -n "$NIC_API2_HOST$NIC_MQTT_HOST" ]; then
    ROLE=all
else
    ROLE=backend
fi

# Proxy settings — applied to this script and all child processes
export http_proxy="http://192.0.2.12:8080"
export https_proxy="http://192.0.2.12:8080"
export HTTP_PROXY="http://192.0.2.12:8080"
export HTTPS_PROXY="http://192.0.2.12:8080"
export ftp_proxy="http://192.0.2.12:8080"
export FTP_PROXY="http://192.0.2.12:8080"
export no_proxy="localhost,127.0.0.1,10.192.136.0/24"
export NO_PROXY="$no_proxy"

# Copies shipped to the other VMs have no .git — they run whatever the control VM sent.
if [ -d .git ]; then
    git pull
fi

STEP="start"
trap 'echo "NIC_deploy: FAILED during: $STEP" >&2' ERR

cleanup_host() {
    # Run with sudo — scripts have their own env/Docker setup
    sudo rm -f /var/log/*.gz
    sudo find /var/log -maxdepth 1 -type f -name '*-????????' -delete
    sudo journalctl --vacuum-size=100M
    # Only truncate regular files — some servers have these as directories or not at all
    for f in mail.log mail.info mail.warn mail.err mail syslog.1 warn sudo.log aide; do
        if sudo test -f "/var/log/$f"; then sudo truncate -s 0 "/var/log/$f"; fi
    done

    sudo docker system prune -f
}

# Wait until this VM's API answers HTTP (any non-5xx), so a broken build stops the
# rollout before the next API VM is touched.
wait_api() {
    local code
    for _ in $(seq 1 45); do
        code=$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' -m 5 \
               http://127.0.0.1:2000/api/session/verify/ || true)
        if [ "$code" -ge 200 ] 2>/dev/null && [ "$code" -lt 500 ]; then
            echo "API is answering on :2000 (HTTP $code)"
            return 0
        fi
        sleep 2
    done
    echo "API did not come up on :2000 (last HTTP code: ${code:-none})" >&2
    sudo docker logs --tail 30 skytron-backend-api-container >&2 || true
    return 1
}

run_reporter_if_broker() {
    # Co-located broker (dev): keep the reporter on the current code too.
    if pgrep -x mosquitto >/dev/null; then
        sudo ./run_mqtt_reporter.sh "$@" || echo "WARN: MQTT IP reporter not deployed (see above)"
    fi
}

role_api() {
    cleanup_host
    sudo SKIP_BUILD="${SKIP_BUILD:-}" ./run_with_host_storage.sh
    if [ "$1" = "--migrate" ]; then
        sudo docker exec skytron-backend-api-container python manage.py migrate
    fi
    wait_api
}

# ---------------------------------------------------------------- multi-VM (control VM)
REMOTE_DIR="${NIC_REMOTE_DIR:-/opt/skytron_deploy/Skytrack_Backend}"
SSH_USER="${NIC_SSH_USER:-Admin}"
SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 -o ServerAliveInterval=30
          -o NumberOfPasswordPrompts=1 -o LogLevel=ERROR)

vm_pass() {
    case "$1" in
        "$NIC_API2_HOST") echo "$NIC_API2_PASS" ;;
        "$NIC_MQTT_HOST") echo "$NIC_MQTT_PASS" ;;
    esac
}

is_this_vm() {
    hostname -I | tr ' ' '\n' | grep -qxF "$1"
}

# with_auth HOST ssh|scp ARGS...: run ssh/scp with HOST's password from .env, through
# sshpass if installed, else OpenSSH's own SSH_ASKPASS (OpenSSH >= 8.4) - nothing to
# install. Either way the password never appears in a process list.
# No password configured for HOST = SSH key only.
with_auth() {
    local pass
    pass=$(vm_pass "$1")
    shift
    if [ -z "$pass" ]; then
        "$1" -o BatchMode=yes "${@:2}"
    elif command -v sshpass >/dev/null; then
        SSHPASS="$pass" sshpass -e "$@"
    else
        NIC_SSH_PASS="$pass" SSH_ASKPASS="$WORK/askpass" SSH_ASKPASS_REQUIRE=force "$@"
    fi
}

# on_vm HOST CMD: run CMD with bash as root on HOST. sudo gets the password on stdin.
on_vm() {
    local host=$1 pass
    shift
    pass=$(vm_pass "$host")
    if [ -n "$pass" ]; then
        printf '%s\n' "$pass" | with_auth "$host" ssh "${SSH_OPTS[@]}" "$SSH_USER@$host" \
            "sudo -S -p '' bash -c $(printf '%q' "$*")"
    else
        with_auth "$host" ssh "${SSH_OPTS[@]}" "$SSH_USER@$host" "sudo -n bash -c $(printf '%q' "$*")"
    fi
}

# to_vm HOST LOCAL_FILE REMOTE_PATH
to_vm() {
    with_auth "$1" scp -q "${SSH_OPTS[@]}" "$2" "$SSH_USER@$1:$3"
}

# Base images the builds need; copied over if a VM cannot pull them itself.
ensure_images() {
    local host=$1 img
    for img in redis:7-alpine; do
        if on_vm "$host" "docker image inspect $img >/dev/null 2>&1"; then
            continue
        fi
        echo "  copying image $img to $host"
        sudo docker image inspect "$img" >/dev/null 2>&1 || sudo docker pull "$img"
        sudo docker save "$img" | gzip > "$WORK/image.tgz"
        to_vm "$host" "$WORK/image.tgz" /tmp/skytron_image.tgz
        on_vm "$host" "gunzip -c /tmp/skytron_image.tgz | docker load && rm -f /tmp/skytron_image.tgz"
    done
}

# Image id out of remote output, ignoring any login banner text
sha_only() {
    grep -o 'sha256:[0-9a-f]\{64\}' | tail -1 || true
}

# remote_role HOST IMAGE CONTAINER ROLE: copy this VM's IMAGE to HOST (unless HOST already
# has that exact image), run ROLE there without rebuilding, then check CONTAINER really
# runs it. Images are only built here: the other VMs' builds cannot reach Debian
# security updates through the proxy, and this way every VM runs the identical image.
remote_role() {
    local host=$1 img=$2 ctr=$3 role=$4 want have
    want=$(sudo docker image inspect -f '{{.Id}}' "$img")
    have=$(on_vm "$host" "docker image inspect -f '{{.Id}}' $img 2>/dev/null || true" | sha_only)
    if [ "$have" != "$want" ]; then
        echo "  copying image $img to $host"
        sudo docker save "$img" | gzip -1 > "$WORK/image.tgz"
        to_vm "$host" "$WORK/image.tgz" /tmp/skytron_image.tgz
        rm -f "$WORK/image.tgz"
        on_vm "$host" "gunzip -c /tmp/skytron_image.tgz | docker load && rm -f /tmp/skytron_image.tgz"
    fi
    on_vm "$host" "cd '$REMOTE_DIR' && SKIP_BUILD=1 ./NIC_deploy.sh $role"
    have=$(on_vm "$host" "docker inspect -f '{{.Image}}' $ctr 2>/dev/null || true" | sha_only)
    if [ "$have" != "$want" ]; then
        echo "$ctr on $host is not running the $img image built here" >&2
        return 1
    fi
    echo "  $ctr on $host runs the same image as this VM (${want:7:12})"
}

# Replace REMOTE_DIR on HOST with this VM's tracked files + .env
ship() {
    local host=$1
    STEP="copying code to $host"
    echo "== $STEP"
    on_vm "$host" "command -v docker >/dev/null" \
        || { echo "Docker is not installed on $host" >&2; return 1; }
    ensure_images "$host"
    to_vm "$host" "$WORK/code.tgz" /tmp/skytron_deploy.tgz
    to_vm "$host" "$WORK/env" /tmp/skytron_deploy.env
    on_vm "$host" "set -e; D='$REMOTE_DIR'
        rm -rf \"\$D.new\"; mkdir -p \"\$D.new\"
        tar -xzf /tmp/skytron_deploy.tgz -C \"\$D.new\"
        install -m 600 /tmp/skytron_deploy.env \"\$D.new/.env\"
        rm -f /tmp/skytron_deploy.tgz /tmp/skytron_deploy.env
        rm -rf \"\$D.old\"; if [ -d \"\$D\" ]; then mv \"\$D\" \"\$D.old\"; fi
        mv \"\$D.new\" \"\$D\"; rm -rf \"\$D.old\""
}

deploy_all() {
    if [ -z "$REDIS_HOST" ]; then
        echo "Set REDIS_HOST/REDIS_PASSWORD in $ENV_FILE first: without a shared Redis each VM" >&2
        echo "keeps its own sessions, OTP state and rate limits (see the NIC multi-VM block)." >&2
        exit 1
    fi
    local remotes=() h
    for h in $NIC_MQTT_HOST $NIC_API2_HOST; do
        if ! is_this_vm "$h" && [[ ! " ${remotes[*]} " =~ " $h " ]]; then
            remotes+=("$h")
        fi
    done
    WORK=$(mktemp -d)
    trap 'rm -rf "$WORK"' EXIT
    # SSH_ASKPASS helper for with_auth: prints the password ssh is given in NIC_SSH_PASS
    printf '#!/bin/sh\nprintf "%%s\\n" "$NIC_SSH_PASS"\n' > "$WORK/askpass"
    chmod 700 "$WORK/askpass"
    if [ -n "$NIC_API2_PASS$NIC_MQTT_PASS" ] && ! command -v sshpass >/dev/null; then
        local v
        v=$(ssh -V 2>&1 | sed -n 's/^OpenSSH_\([0-9]*\.[0-9]*\).*/\1/p')
        if ! awk -v v="$v" 'BEGIN { exit !(v + 0 >= 8.4) }'; then
            echo "OpenSSH $v here is too old for password logins without sshpass." >&2
            echo "Install sshpass (sudo apt-get install sshpass) or set up SSH keys." >&2
            exit 1
        fi
    fi

    # Fail fast on a wrong password / unreachable VM, before anything is redeployed
    for h in "${remotes[@]}"; do
        STEP="checking SSH + sudo on $h"
        echo "== $STEP"
        on_vm "$h" "true" </dev/null
    done

    STEP="packing code"
    echo "== $STEP"
    git rev-parse --short HEAD > "$WORK/DEPLOYED_COMMIT"
    git ls-files -z | tar --null --ignore-failed-read -czf "$WORK/code.tgz" \
        -T - -C "$WORK" DEPLOYED_COMMIT
    # VM passwords stay on this VM only
    grep -Ev '^[[:space:]]*(export[[:space:]]+)?NIC_[A-Z0-9_]*PASS=' "$ENV_FILE" > "$WORK/env"
    echo "Deploying commit $(cat "$WORK/DEPLOYED_COMMIT") to: this VM ${remotes[*]}"

    # Build the MQTT image before touching any VM, so a failed build changes nothing
    if [ -n "$NIC_MQTT_HOST" ] && ! is_this_vm "$NIC_MQTT_HOST"; then
        STEP="building the MQTT processor image here"
        echo "== $STEP"
        sudo BUILD_ONLY=1 ./run_mqtt.sh
    fi

    for h in "${remotes[@]}"; do
        ship "$h"
    done

    STEP="shared Redis on $REDIS_HOST"
    echo "== $STEP"
    if is_this_vm "$REDIS_HOST"; then
        sudo ./run_redis.sh
    elif [[ " ${remotes[*]} " =~ " $REDIS_HOST " ]]; then
        on_vm "$REDIS_HOST" "cd '$REMOTE_DIR' && ./run_redis.sh"
    else
        echo "REDIS_HOST $REDIS_HOST is not one of the deploy VMs - assuming it is managed elsewhere"
    fi

    STEP="API + migrations on this VM"
    echo "== $STEP"
    role_api --migrate

    if [ -n "$NIC_API2_HOST" ] && ! is_this_vm "$NIC_API2_HOST"; then
        STEP="API on $NIC_API2_HOST"
        echo "== $STEP"
        remote_role "$NIC_API2_HOST" skytron-backend-api skytron-backend-api-container api
    fi

    if [ -n "$NIC_MQTT_HOST" ]; then
        STEP="MQTT processor on $NIC_MQTT_HOST"
        echo "== $STEP"
        if is_this_vm "$NIC_MQTT_HOST"; then
            sudo ./run_mqtt.sh
        else
            remote_role "$NIC_MQTT_HOST" skytrack-mqtt-client skytrack-mqtt-client-container mqtt-processor
        fi

        # Only now (the new processor is running) drop MQTT clients left on the API VMs
        # from the single-VM setup; two clients would process every packet twice.
        STEP="removing old MQTT clients from the API VMs"
        if ! is_this_vm "$NIC_MQTT_HOST"; then
            sudo docker rm -f skytrack-mqtt-client-container >/dev/null 2>&1 || true
        fi
        if [ -n "$NIC_API2_HOST" ] && [ "$NIC_API2_HOST" != "$NIC_MQTT_HOST" ] && ! is_this_vm "$NIC_API2_HOST"; then
            on_vm "$NIC_API2_HOST" "docker rm -f skytrack-mqtt-client-container >/dev/null 2>&1 || true"
        fi
    fi

    echo "NIC_deploy: all VMs deployed at commit $(cat "$WORK/DEPLOYED_COMMIT")"
}

case "$ROLE" in
  all)
    deploy_all
    ;;
  backend)
    cleanup_host
    sudo ./run_with_host_storage.sh
    sudo docker exec skytron-backend-api-container python manage.py migrate
    sudo ./run_mqtt.sh
    run_reporter_if_broker "$@"
    ;;
  api)
    role_api "$@"
    ;;
  mqtt-processor)
    cleanup_host
    sudo SKIP_BUILD="${SKIP_BUILD:-}" ./run_mqtt.sh
    run_reporter_if_broker
    ;;
  redis)
    sudo ./run_redis.sh
    ;;
  mqtt-reporter)
    cleanup_host
    sudo ./run_mqtt_reporter.sh "$@"
    ;;
  *)
    echo "Unknown role: $ROLE (use: all | backend | api | mqtt-processor | redis | mqtt-reporter)" >&2
    exit 1
    ;;
esac
