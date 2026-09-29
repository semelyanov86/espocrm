#!/usr/bin/env bash
# Reproduce the stage-01 read-only source audit.
#
#   scripts/audit/run-audit.sh            # full run, new private output dir
#   AUDIT_TS=20260929T1840 scripts/audit/run-audit.sh   # re-use a named output dir
#
# Reads the production server only (SELECT in READ ONLY sessions, ls/stat/find/wc).
# Private outputs (counts, metadata, picklist values) go to $AUDIT_PRIVATE_ROOT/<ts>/ outside Git.
# Only docs/migration/field-map.csv and relations.csv are regenerated inside the repository.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"
OUT="$(audit_outdir)"
echo "private output: $OUT"
date -Is > "$OUT/started_at.txt"

run_sql() { # name [db]
    remote_sql "${2:-$AUDIT_DB}" < "$HERE/sql/$1.sql" > "$OUT/$1.tsv"
    echo "  $1: $(wc -l < "$OUT/$1.tsv") lines"
}
run_remote_py() { # script.py outfile stdin-sql [args]
    local script="$1" out="$2" sql="$3"; shift 3
    local tmp="/tmp/espo_audit_$$_$(basename "$script")"
    scp -q "${AUDIT_SSH_OPTS[@]}" "$HERE/remote/$script" "$AUDIT_HOST:$tmp"
    { echo "SET SESSION TRANSACTION READ ONLY;"; echo "$sql"; } \
        | ssh "${AUDIT_SSH_OPTS[@]}" "$AUDIT_HOST" "sudo -n mysql --batch --default-character-set=utf8mb4 $AUDIT_DB | sudo -n python3 $tmp $*; rm -f $tmp" > "$OUT/$out"
    echo "  $out: $(wc -l < "$OUT/$out") lines"
}

echo "1. schema metadata"
for n in 01_tabs 02_fields 03_columns 04_tables 05_primary_keys 06_shapes; do run_sql "$n"; done

echo "2. generated counts"
python3 "$HERE/gen_sql.py" table-counts "$OUT" > "$OUT/10_table_counts.sql"
remote_sql < "$OUT/10_table_counts.sql" > "$OUT/10_table_counts.tsv"
python3 "$HERE/gen_sql.py" column-counts "$OUT" > "$OUT/11_column_counts.sql"
remote_sql < "$OUT/11_column_counts.sql" > "$OUT/11_column_counts.raw"
python3 "$HERE/gen_sql.py" field-live-counts "$OUT" > "$OUT/12_field_live_counts.sql"
remote_sql < "$OUT/12_field_live_counts.sql" > "$OUT/12_field_live_counts.raw"
python3 "$HERE/gen_sql.py" reference-targets "$OUT" > "$OUT/13_reference_targets.sql"
remote_sql < "$OUT/13_reference_targets.sql" | grep -v '^module	' > "$OUT/13_reference_targets.tsv"
python3 "$HERE/gen_sql.py" picklist-values "$OUT" > "$OUT/14_picklist_values.sql"
remote_sql < "$OUT/14_picklist_values.sql" | grep -v '^module	field' > "$OUT/14_picklist_values.tsv"

echo "3. relations, ACL, workflows, finance, telephony"
for n in 20_relations 21_acl 25_activity_workflows 26_finance 27_payments 28_pbx 31_misc 32_cardinality 33_allocation_check 34_finance_config; do
    run_sql "$n"
done
run_sql 40_cdr asteriskcdrdb
run_sql 35_control_sums_private   # monetary aggregates: private only

echo "4. host-side checks (only counts leave the host)"
run_remote_py template_tokens.py 23_templates.tsv "$(cat "$HERE/sql/23_templates.sql")"
run_remote_py check_attachments.py 22_attachments_files.tsv \
    "SELECT a.attachmentsid, IFNULL(c.setype,'(no crmentity)'), IFNULL(c.deleted,''), a.path, a.name FROM vtiger_attachments a LEFT JOIN vtiger_crmentity c ON c.crmid=a.attachmentsid;" \
    /var/www/serv_itvolga/vtiger7
tmp="/tmp/espo_audit_$$_access.py"
scp -q "${AUDIT_SSH_OPTS[@]}" "$HERE/remote/access_log_usage.py" "$AUDIT_HOST:$tmp"
ssh "${AUDIT_SSH_OPTS[@]}" "$AUDIT_HOST" "sudo -n python3 $tmp; rm -f $tmp" > "$OUT/24_access_usage.tsv"
ssh "${AUDIT_SSH_OPTS[@]}" "$AUDIT_HOST" 'sudo -n bash -s' < "$HERE/remote/telephony_inventory.sh" > "$OUT/29_telephony.txt" 2>&1
tmp="/tmp/espo_audit_$$_cdr.py"
scp -q "${AUDIT_SSH_OPTS[@]}" "$HERE/remote/cdr_overlap.py" "$AUDIT_HOST:$tmp"
ssh "${AUDIT_SSH_OPTS[@]}" "$AUDIT_HOST" "sudo -n mysql --batch --raw asteriskcdrdb -e \"SET SESSION TRANSACTION READ ONLY; SELECT uniqueid, linkedid, calldate, IFNULL(recordingpath,'') FROM cdr\" | sudo -n python3 $tmp; rm -f $tmp" > "$OUT/30_cdr_overlap.tsv"

echo "5. consolidate and build anonymised maps"
python3 "$HERE/consolidate.py" "$OUT"
python3 "$HERE/build_maps.py" "$OUT" "$REPO/docs/migration"
date -Is > "$OUT/finished_at.txt"
echo "done: $OUT"
