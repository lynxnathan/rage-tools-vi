#!/usr/bin/env bash
# Every end-to-end check, headless. Nothing opens on the desktop: the UI scripts run
# under xvfb-run internally.
#
#   tools/e2e_all.sh
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
run() {
  printf '%-40s ' "$1"
  local start=$(date +%s)
  if timeout 1800 bash "$1" >/tmp/e2e-all.log 2>&1; then
    printf 'PASS %3ds\n' "$(( $(date +%s) - start ))"
  else
    printf 'FAIL\n'; tail -3 /tmp/e2e-all.log | sed 's/^/    /'; fail=1
  fi
}
for script in tools/explorer_*e2e*.sh; do run "$script"; done
run tools/e2e_mod.sh
run tools/demo_media.sh
echo
[ $fail -eq 0 ] && echo "PASS" || echo "FAIL"
exit $fail
