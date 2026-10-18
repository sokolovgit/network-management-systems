#!/bin/bash
# Usage: monitor.sh [interval_s] [count] [pattern]
INTERVAL=${1:-3}
COUNT=${2:-5}
PATTERN=${3:-all}
S=/sys/class/net/eth0/statistics
# час беремо з самого вузла: ad-hoc виклик ansible триває ~1 с, і sleep не дає точного інтервалу
CMD="echo \$(date +%s.%N) \$(cat $S/rx_bytes $S/tx_bytes) \$(ss -Htn state established | wc -l)"
declare -A T0 RX0 TX0

echo "час       вузол     стан          RX, KiB/s   TX, KiB/s   TCP"
for ((i = 0; i <= COUNT; i++)); do
    while IFS= read -r line; do
        host=${line%% *}
        if [[ $line != *"(stdout)"* ]]; then
            printf "%-8s  %-8s  %s\n" "$(date +%T)" "$host" UNREACHABLE
            continue
        fi
        read -r t rx tx tcp <<< "${line##*(stdout) }"
        if [[ -n ${T0[$host]} ]]; then
            awk -v c="$(date +%T)" -v h="$host" -v n="$tcp" -v t="$t" -v t0="${T0[$host]}" \
                -v dr=$((rx - RX0[$host])) -v dx=$((tx - TX0[$host])) 'BEGIN { kb = 1024 * (t - t0)
                printf "%-8s  %-8s  %-11s  %10.1f  %10.1f  %4s\n", c, h, "OK", dr / kb, dx / kb, n }'
        fi
        T0[$host]=$t RX0[$host]=$rx TX0[$host]=$tx
    done < <(ansible "$PATTERN" -m shell -a "$CMD" -o -u root 2>/dev/null)
    if ((i < COUNT)); then sleep "$INTERVAL"; fi
done
