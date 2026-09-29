#!/usr/bin/env bash
# Run ON the source host via sudo. Read-only telephony inventory: prints versions, counts,
# date ranges and config key presence. Never prints secrets, phone numbers or file names.
set -uo pipefail

echo "## asterisk"
asterisk -V 2>/dev/null || echo "asterisk binary: missing"
systemctl is-active asterisk 2>/dev/null | sed 's/^/service: /'
asterisk -rx "core show uptime" 2>/dev/null | sed 's/^/uptime: /'
asterisk -rx "cdr show status" 2>/dev/null | grep -E -i "enabled|mode|backend|csv|odbc|adaptive" | sed 's/^/cdr: /'
asterisk -rx "module show like cdr" 2>/dev/null | tail -n +2 | awk '{print "cdr_module:", $1, $NF}'
asterisk -rx "module show like mixmonitor" 2>/dev/null | tail -n +2 | awk '{print "mon_module:", $1}'

echo "## ami"
if [ -f /etc/asterisk/manager.conf ]; then
    awk -F= '/^\s*\[/{sect=$0} /^\s*(enabled|port|bindaddr|webenabled)\s*=/{gsub(/[ \t]/,"",$1); gsub(/[ \t;].*/,"",$2); print "manager.conf", sect, $1"="$2}' /etc/asterisk/manager.conf
    echo "manager.conf user sections: $(grep -c -E '^\s*\[[^]]+\]' /etc/asterisk/manager.conf) (incl. [general])"
    ls /etc/asterisk/manager.d 2>/dev/null | wc -l | sed 's/^/manager.d files: /'
else
    echo "manager.conf: missing"
fi
echo "## listening ports of interest"
ss -ltnup 2>/dev/null | awk 'NR>1 {print $1, $5, $7}' | grep -E ':(5038|8088|8089|5000|5060|5061|4569)\b' | sed -E 's/pid=[0-9]+,fd=[0-9]+//g'

echo "## dialplan hooks"
for f in /etc/asterisk/extensions.conf /etc/asterisk/extensions*.conf; do
    [ -f "$f" ] || continue
    echo "$f: MixMonitor=$(grep -c MixMonitor "$f") AGI=$(grep -c -E 'AGI\(' "$f") System=$(grep -c -E 'System\(' "$f") CURL=$(grep -c -i curl "$f") vtiger=$(grep -c -i vtiger "$f")"
done | sort -u

echo "## cdr-csv"
for f in /var/log/asterisk/cdr-csv/*; do
    [ -f "$f" ] || continue
    lines=$(wc -l < "$f")
    # CDR CSV: field 10 = start time (quoted). Only the date range is printed.
    range=$(awk -F'","' '{print substr($10,1,10)}' "$f" | grep -E '^[0-9]{4}-' | sort | sed -n '1p;$p' | tr '\n' ' ')
    months=$(awk -F'","' '{print substr($10,1,7)}' "$f" | grep -E '^[0-9]{4}-' | sort | uniq -c | awk '{printf "%s:%s ", $2, $1}')
    echo "$(basename "$f") lines=$lines size=$(stat -c %s "$f") range=[$range] months=[$months]"
done
ls -la /var/log/asterisk/ 2>/dev/null | awk 'NR>1 {print "logdir:", $1, $5, $6, $7, $8, ($9 ~ /^(messages|full|queue_log|security)/ ? $9 : ($9 ~ /cdr/ ? $9 : "(other)"))}'

echo "## monitor"
MON=/var/spool/asterisk/monitor
if [ -d "$MON" ]; then
    echo "monitor owner: $(stat -c '%U:%G %a' "$MON")"
    echo "monitor total files: $(find "$MON" -type f | wc -l) bytes: $(du -sb "$MON" | cut -f1)"
    find "$MON" -type f -printf '%TY-%Tm %s %f\n' | awk '{split($3,a,"."); ext=a[length(a)]; m[$1" "ext]++; s[$1" "ext]+=$2} END{for(k in m) print "monitor month/ext:", k, m[k], s[k]}' | sort
    echo "monitor zero-byte files: $(find "$MON" -type f -size 0 | wc -l)"
fi
echo "## other recording/cdr locations"
for d in /var/spool/asterisk /var/lib/asterisk /opt /srv /home/sergey /root /var/backups; do
    [ -d "$d" ] || continue
    n=$(find "$d" -maxdepth 6 -type f \( -iname '*.wav' -o -iname '*.mp3' -o -iname '*.gsm' -o -iname '*.ogg' \) -not -path '/var/lib/asterisk/sounds/*' -not -path '/var/lib/asterisk/moh/*' 2>/dev/null | wc -l)
    c=$(find "$d" -maxdepth 6 -type f \( -iname 'Master*.csv*' -o -iname '*cdr*' \) 2>/dev/null | wc -l)
    echo "$d audio_files=$n cdr_like_files=$c"
done
echo "## connector"
systemctl list-units --all --no-legend 2>/dev/null | grep -i -E 'connector|vtiger|pbx|asterisk' | awk '{print "unit:", $1, $3, $4}'
docker ps -a --format '{{.Names}} {{.Image}} {{.Status}}' 2>/dev/null | grep -i -E 'connector|asterisk|pbx|php74' | sed 's/^/container: /'
