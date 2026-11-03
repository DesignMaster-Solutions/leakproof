#!/usr/bin/env bash
# Sync the repo to the VM, rebuild the sandbox image if needed, restart the app, smoke-test the public URL.
set -euo pipefail
cd "$(dirname "$0")/.."
HOST=${HOST:-leakproof}
echo "deploy: start $(date -u +%FT%TZ) $(git rev-parse --short HEAD)"
rsync -a --delete --exclude .venv --exclude .git --exclude data ./ "$HOST":/opt/leakproof/
ssh "$HOST" 'set -e; cd /opt/leakproof
  .venv/bin/pip install -q -r requirements.txt
  docker build -q -t leakproof-sandbox sandbox >/dev/null
  install -m 644 infra/leakproof.service /etc/systemd/system/leakproof.service
  install -m 644 infra/Caddyfile /etc/caddy/Caddyfile
  systemctl daemon-reload && systemctl enable -q --now leakproof && systemctl restart leakproof && systemctl reload caddy
  for i in $(seq 1 30); do curl -sf -o /dev/null http://127.0.0.1:8000/api/config && break; sleep 1; done'
for i in 1 2 3 4 5 6; do  # first deploy waits for the Let's Encrypt certificate
  code=$(curl -s -o /dev/null -w "%{http_code}" -m 30 https://leakproof.designmastersolutions.com/api/config || true)
  [ "$code" = 200 ] && break; sleep 5
done
echo "deploy: https /api/config -> $code"
rc=0; [ "$code" = 200 ] || rc=1
echo "deploy: fim rc=$rc"
exit $rc
