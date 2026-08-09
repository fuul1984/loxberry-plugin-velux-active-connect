#!/bin/bash
set -u
LBROOT="${5:-${LBHOMEDIR:-/opt/loxberry}}"
LOGDIR="$LBROOT/log/plugins/veluxactive"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/dependencies.log"
exec >>"$LOG" 2>&1

echo "===== $(date '+%F %T') VELUX Active dependency check ====="

check_crypto() {
  python3 -c 'import cryptography; print(cryptography.__version__)' 2>/dev/null
}

version="$(check_crypto || true)"
if [ -n "$version" ]; then
  echo "cryptography bereits vorhanden: $version"
  exit 0
fi

echo "cryptography fehlt."

if command -v apt-get >/dev/null 2>&1; then
  echo "Versuche Debian-Paket python3-cryptography ..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update || echo "WARNUNG: apt-get update fehlgeschlagen"
  apt-get install -y python3-cryptography || true
fi

version="$(check_crypto || true)"
if [ -n "$version" ]; then
  echo "cryptography erfolgreich über Debian installiert: $version"
  exit 0
fi

echo "Debian-Paket nicht ausreichend/verfügbar. Versuche pip-Fallback ..."

if ! python3 -m pip --version >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    apt-get install -y python3-pip || true
  fi
fi

if python3 -m pip --version >/dev/null 2>&1; then
  python3 -m pip install --break-system-packages cryptography || \
  python3 -m pip install cryptography || true
fi

version="$(check_crypto || true)"
if [ -n "$version" ]; then
  echo "cryptography erfolgreich über pip installiert: $version"
  exit 0
fi

echo "FEHLER: cryptography konnte nicht automatisch installiert werden."
exit 1
