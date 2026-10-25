#!/bin/bash
# Shared Redis for the multi-VM NIC setup. Both API VMs and the MQTT processor point
# REDIS_URL here (sessions, OTP state, rate limits, RBAC cache, device IPs), so a request
# sees the same state whichever API VM the load balancer picks.
#
# Settings from .env: REDIS_HOST (this VM's private IP), REDIS_PORT, REDIS_PASSWORD,
# REDIS_ALLOWED_IPS (the other VMs). Unlike the single-VM Redis in run_with_host_storage.sh
# it is NOT recreated on every deploy - only when these settings change - and keeps its
# data in the skytron-redis-data volume, so a deploy does not log everyone out.
set -e

ENV_FILE="${ENV_FILE:-.env}"
if [ ! -f "$ENV_FILE" ] && [ -f ".renv" ]; then
  ENV_FILE=".renv"
fi
if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file not found: $ENV_FILE"
  exit 1
fi
source "$ENV_FILE"

: "${REDIS_HOST:?REDIS_HOST is not set in $ENV_FILE}"
# Goes into a redis:// URL unescaped, so letters/digits only
if ! [[ "$REDIS_PASSWORD" =~ ^[A-Za-z0-9]{24,}$ ]]; then
  echo "REDIS_PASSWORD must be 24+ letters/digits (generate: openssl rand -hex 24)"
  exit 1
fi
PORT="${REDIS_PORT:-6379}"
NAME=skytron-redis
CONF=$(printf '%s' "$REDIS_HOST:$PORT:$REDIS_PASSWORD" | sha256sum | cut -c1-16)

if [ "$(docker inspect -f '{{.State.Running}} {{index .Config.Labels "skytron.redis.conf"}}' $NAME 2>/dev/null)" = "true $CONF" ]; then
  echo "Shared Redis already running with these settings - left as is"
else
  echo "Starting shared Redis on $REDIS_HOST:$PORT ..."
  docker rm -f $NAME >/dev/null 2>&1 || true
  # Published on the private IP only, never 0.0.0.0
  docker run -d --name $NAME --restart unless-stopped \
    --label skytron.redis.conf="$CONF" \
    -p "$REDIS_HOST:$PORT:6379" \
    -v skytron-redis-data:/data \
    redis:7-alpine \
    redis-server --appendonly yes --requirepass "$REDIS_PASSWORD"
fi

# Docker-published ports bypass ufw, so restrict them in DOCKER-USER: only the listed VMs
# and containers on this VM (docker bridge 172.16/12) may reach Redis. Re-applied on every
# deploy; after a reboot only the password protects it until the next deploy.
if [ -n "$REDIS_ALLOWED_IPS" ]; then
  iptables -N SKYTRON-REDIS 2>/dev/null || iptables -F SKYTRON-REDIS
  for src in $REDIS_ALLOWED_IPS 172.16.0.0/12; do
    iptables -A SKYTRON-REDIS -s "$src" -j RETURN
  done
  iptables -A SKYTRON-REDIS -j DROP
  iptables -C DOCKER-USER -p tcp --dport 6379 -j SKYTRON-REDIS 2>/dev/null \
    || iptables -I DOCKER-USER -p tcp --dport 6379 -j SKYTRON-REDIS
  echo "Redis reachable only from: $REDIS_ALLOWED_IPS (+ local containers)"
else
  echo "WARN: REDIS_ALLOWED_IPS not set - Redis is open to the whole private network (password only)"
fi

for _ in $(seq 1 20); do
  if docker exec $NAME redis-cli -a "$REDIS_PASSWORD" --no-auth-warning ping 2>/dev/null | grep -q PONG; then
    echo "Shared Redis is up at $REDIS_HOST:$PORT"
    exit 0
  fi
  sleep 1
done
echo "Shared Redis did not answer PING" >&2
docker logs --tail 20 $NAME >&2
exit 1
