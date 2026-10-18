#!/bin/bash
# Usage: monitor.sh [host] [interval_s] [count]
HOST=${1:-10.10.0.2}
INTERVAL=${2:-2}
COUNT=${3:-10}
AUTH=(-v3 -a MD5 -A 123456789 -X 123456789 -l authNoPriv -u sokolov)

get() { snmpget "${AUTH[@]}" -Oqv "$HOST" "$@"; }

IDX=$(snmpwalk "${AUTH[@]}" -Oq "$HOST" .1.3.6.1.2.1.2.2.1.2 | awk '$2 == "eth0" { n = split($1, a, "."); print a[n] }')
if [ -z "$IDX" ]; then
    echo "$HOST: агент не відповідає або немає eth0" >&2
    exit 1
fi
echo "Агент: $(get .1.3.6.1.2.1.1.5.0), eth0 = ifIndex $IDX"
echo "час        RX, KiB/s   TX, KiB/s   проц.   load"

read -r RX0 TX0 < <(get .1.3.6.1.2.1.31.1.1.1.6.$IDX .1.3.6.1.2.1.31.1.1.1.10.$IDX | xargs)
for ((i = 0; i < COUNT; i++)); do
    sleep "$INTERVAL"
    read -r RX TX PROCS LOAD < <(get .1.3.6.1.2.1.31.1.1.1.6.$IDX .1.3.6.1.2.1.31.1.1.1.10.$IDX \
        .1.3.6.1.2.1.25.1.6.0 .1.3.6.1.4.1.2021.10.1.3.1 | tr -d '"' | xargs)
    awk -v t="$(date +%T)" -v dr=$((RX - RX0)) -v dt=$((TX - TX0)) -v s="$INTERVAL" -v p="$PROCS" -v l="$LOAD" \
        'BEGIN { printf "%-8s  %10.1f  %10.1f  %6s  %5s\n", t, dr / 1024 / s, dt / 1024 / s, p, l }'
    RX0=$RX TX0=$TX
done
