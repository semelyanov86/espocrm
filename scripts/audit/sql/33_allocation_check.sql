-- Allocation evidence quality: relation-table links vs related_to (live records, aggregates only).
SET @eps := 0.005;
WITH rel AS (
  SELECT r.crmid invoiceid, r.relcrmid payid FROM vtiger_crmentityrel r
  JOIN vtiger_crmentity ci ON ci.crmid=r.crmid AND ci.deleted=0 AND ci.setype='Invoice'
  JOIN vtiger_crmentity cp ON cp.crmid=r.relcrmid AND cp.deleted=0 AND cp.setype='SPPayments'),
per_inv AS (SELECT invoiceid, COUNT(*) n FROM rel GROUP BY invoiceid)
SELECT 'rel_per_invoice' k, MAX(n) max_payments, SUM(n>5) invoices_gt5, COUNT(*) invoices FROM per_inv;
WITH rel AS (
  SELECT r.crmid invoiceid, r.relcrmid payid FROM vtiger_crmentityrel r
  JOIN vtiger_crmentity ci ON ci.crmid=r.crmid AND ci.deleted=0 AND ci.setype='Invoice'
  JOIN vtiger_crmentity cp ON cp.crmid=r.relcrmid AND cp.deleted=0 AND cp.setype='SPPayments')
SELECT 'rel_vs_related_to' k,
  SUM(p.related_to=rel.invoiceid) same_invoice, SUM(p.related_to IS NOT NULL AND p.related_to<>0 AND p.related_to<>rel.invoiceid) other_invoice,
  SUM(p.related_to IS NULL OR p.related_to=0) related_empty, SUM(cf.cf_1204<>'' AND cf.cf_1204 IS NOT NULL) from_bank_import, COUNT(*) n
FROM rel JOIN sp_payments p ON p.payid=rel.payid JOIN sp_paymentscf cf ON cf.payid=p.payid;
WITH alloc AS (
  SELECT DISTINCT x.invoiceid, x.payid FROM (
    SELECT p.related_to invoiceid, p.payid FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0 WHERE p.related_to IS NOT NULL AND p.related_to<>0
    UNION ALL
    SELECT r.crmid, r.relcrmid FROM vtiger_crmentityrel r JOIN vtiger_crmentity ci ON ci.crmid=r.crmid AND ci.deleted=0 AND ci.setype='Invoice'
    JOIN vtiger_crmentity cp ON cp.crmid=r.relcrmid AND cp.deleted=0 AND cp.setype='SPPayments') x),
multi AS (SELECT payid, COUNT(DISTINCT invoiceid) ninv FROM alloc GROUP BY payid)
SELECT 'union_alloc' k, COUNT(*) payments_allocated, SUM(ninv>1) payments_in_2plus_invoices, MAX(ninv) max_invoices_per_payment FROM multi;
