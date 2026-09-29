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
python3 "$HERE/gen_sql.py" table-live-counts "$OUT" > "$OUT/15_table_live_counts.sql"
remote_sql < "$OUT/15_table_live_counts.sql" > "$OUT/15_table_live_counts.raw"

echo "3. relations, ACL, workflows, finance, telephony"
for n in 20_relations 21_acl 25_activity_workflows 26_finance 27_payments 28_pbx 31_misc 32_cardinality 33_allocation_check \
         34_finance_config 36_rounding 37_timezone; do
    run_sql "$n"
done
run_sql 40_cdr asteriskcdrdb
run_sql 35_control_sums_private   # monetary aggregates: private only

echo "4. host-side checks (only counts leave the host; scripts run inline, no files on the host)"
remote_sql_py "$AUDIT_DB" template_tokens.py < "$HERE/sql/23_templates.sql" > "$OUT/23_templates.tsv"
remote_sql_py "$AUDIT_DB" check_attachments.py /var/www/serv_itvolga/vtiger7 > "$OUT/22_attachments_files.tsv" <<'SQL'
SELECT a.attachmentsid, IFNULL(c.setype,'(no crmentity)'), IFNULL(c.deleted,''), a.path, a.name
FROM vtiger_attachments a LEFT JOIN vtiger_crmentity c ON c.crmid=a.attachmentsid;
SQL
remote_py access_log_usage.py > "$OUT/24_access_usage.tsv"
ssh "${AUDIT_SSH_OPTS[@]}" "$AUDIT_HOST" 'sudo -n bash -s' < "$HERE/remote/telephony_inventory.sh" > "$OUT/29_telephony.txt" 2>&1
remote_sql_py asteriskcdrdb cdr_overlap.py > "$OUT/30_cdr_overlap.tsv" <<'SQL'
SELECT uniqueid, linkedid, calldate, IFNULL(recordingpath,''), dst, dstchannel, billsec, sequence FROM cdr;
SQL
remote_sql_py asteriskcdrdb wav_csv_match.py > "$OUT/38_wav_csv_match.tsv" <<'SQL'
SELECT uniqueid, calldate, IFNULL(recordingpath,''), src, dst FROM cdr;
SQL
remote_sql_py "$AUDIT_DB" attachment_tz.py /var/www/serv_itvolga/vtiger7 > "$OUT/39_attachment_tz.tsv" <<'SQL'
SELECT a.attachmentsid, c.createdtime, a.path, a.name FROM vtiger_attachments a JOIN vtiger_crmentity c ON c.crmid=a.attachmentsid AND c.deleted=0;
SQL
remote_sql_py "$AUDIT_DB" login_tz.py > "$OUT/39_login_tz.tsv" <<'SQL'
SELECT login_time FROM vtiger_loginhistory WHERE login_time >= NOW() - INTERVAL 20 DAY;
SQL
for f in 22_attachments_files.tsv 23_templates.tsv 24_access_usage.tsv 29_telephony.txt 30_cdr_overlap.tsv \
         38_wav_csv_match.tsv 39_attachment_tz.tsv 39_login_tz.tsv; do
    echo "  $f: $(wc -l < "$OUT/$f") lines"
done

echo "5. consolidate and build anonymised maps"
python3 "$HERE/consolidate.py" "$OUT"
python3 "$HERE/build_maps.py" "$OUT" "$REPO/docs/migration"
date -Is > "$OUT/finished_at.txt"
echo "done: $OUT"
