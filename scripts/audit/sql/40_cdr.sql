-- Run against asteriskcdrdb. Shape of MySQL CDR (no numbers).
SELECT 'cdr_cols' k, GROUP_CONCAT(column_name ORDER BY ordinal_position) cols FROM information_schema.columns WHERE table_schema='asteriskcdrdb' AND table_name='cdr';
SELECT 'cdr_month' k, DATE_FORMAT(calldate,'%Y-%m') ym, COUNT(*) n, COUNT(DISTINCT linkedid) linked, COUNT(DISTINCT uniqueid) uniq, SUM(recordingpath IS NOT NULL AND recordingpath<>'') with_rec, SUM(disposition='ANSWERED') answered FROM cdr GROUP BY 2 ORDER BY 2;
SELECT 'cdr_ctx' k, dcontext, disposition, COUNT(*) n FROM cdr GROUP BY 2,3 ORDER BY 4 DESC;
