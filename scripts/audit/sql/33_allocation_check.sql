-- Payment allocation evidence as a strict partition of live payments (aggregates only).
-- rt = sp_payments.related_to target; rel = live Invoice<->live payment pairs in vtiger_crmentityrel (both directions).
WITH p AS (
  SELECT pay.payid, pay.related_to rt, rc.setype rt_setype, rc.deleted rt_deleted
  FROM sp_payments pay JOIN vtiger_crmentity c ON c.crmid=pay.payid AND c.deleted=0
  LEFT JOIN vtiger_crmentity rc ON rc.crmid=pay.related_to),
rel AS (
  SELECT DISTINCT x.payid, x.invoiceid FROM (
    SELECT r.relcrmid payid, r.crmid invoiceid FROM vtiger_crmentityrel r
    UNION ALL SELECT r.crmid, r.relcrmid FROM vtiger_crmentityrel r) x
  JOIN vtiger_crmentity ci ON ci.crmid=x.invoiceid AND ci.deleted=0 AND ci.setype='Invoice'
  JOIN vtiger_crmentity cp ON cp.crmid=x.payid AND cp.deleted=0 AND cp.setype='SPPayments'),
a AS (SELECT payid, COUNT(*) nrel FROM rel GROUP BY payid),
cls AS (
  SELECT p.payid,
    CASE
      WHEN p.rt_setype='Invoice' AND p.rt_deleted=0 AND EXISTS (SELECT 1 FROM rel WHERE rel.payid=p.payid AND rel.invoiceid=p.rt) THEN 'both_same_invoice'
      WHEN p.rt_setype='Invoice' AND p.rt_deleted=0 AND IFNULL(a.nrel,0)>0 THEN 'conflict_rel_other_invoice'
      WHEN p.rt_setype='Invoice' AND p.rt_deleted=0 THEN 'related_to_invoice_only'
      WHEN p.rt_setype='SalesOrder' AND p.rt_deleted=0 THEN CONCAT('related_to_salesorder', IF(IFNULL(a.nrel,0)>0,'_plus_rel',''))
      WHEN p.rt_setype IS NOT NULL AND p.rt_deleted=1 THEN CONCAT('related_to_deleted_', p.rt_setype, IF(IFNULL(a.nrel,0)>0,'_plus_rel',''))
      WHEN IFNULL(a.nrel,0)>0 THEN 'rel_only'
      ELSE 'unallocated' END category,
    IFNULL(a.nrel,0) nrel
  FROM p LEFT JOIN a ON a.payid=p.payid)
SELECT 'alloc_partition' k, category, COUNT(*) payments, SUM(nrel>1) with_2plus_rel FROM cls GROUP BY 2 ORDER BY 2;
WITH rel AS (
  SELECT DISTINCT r.crmid invoiceid, r.relcrmid payid FROM vtiger_crmentityrel r
  JOIN vtiger_crmentity ci ON ci.crmid=r.crmid AND ci.deleted=0 AND ci.setype='Invoice'
  JOIN vtiger_crmentity cp ON cp.crmid=r.relcrmid AND cp.deleted=0 AND cp.setype='SPPayments')
SELECT 'rel_per_invoice' k, MAX(n) max_payments, SUM(n>5) invoices_gt5, COUNT(*) invoices FROM (SELECT invoiceid, COUNT(*) n FROM rel GROUP BY invoiceid) t;
