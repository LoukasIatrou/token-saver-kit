#!/usr/bin/env sh
# macOS / Linux entry point. All the work happens in install.py.
set -e
cd "$(dirname "$0")"
for py in python3 python; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
    exec "$py" install.py "$@"
  fi
done
echo "Python 3.11+ is required: https://www.python.org/downloads/" >&2
exit 1
