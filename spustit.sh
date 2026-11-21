#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ -f .venv/bin/python ]; then
  exec .venv/bin/python app.py "$@"
fi
if python3 -c 'import PySide6' >/dev/null 2>&1; then
  exec python3 app.py "$@"
fi
printf '\nChybí PySide6. Instalace (jen jednou):\n\n'
printf '  python3 -m venv .venv\n'
printf '  .venv/bin/python -m pip install -r requirements.txt\n'
printf '  ./spustit.sh\n\n'
exit 1
