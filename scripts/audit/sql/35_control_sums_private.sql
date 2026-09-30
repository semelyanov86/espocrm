-- PRIVATE OUTPUT: monetary control sums per document type and year (business-confidential, keep outside Git).
SELECT 'doc_sums' k, 'Invoice' m, YEAR(h.invoicedate) y, h.taxtype, COUNT(*) n, SUM(h.subtotal) subtotal, SUM(h.pre_tax_total) pre_tax, SUM(h.total) total, SUM(h.balance) balance
FROM vtiger_invoice h JOIN vtiger_crmentity c ON c.crmid=h.invoiceid AND c.deleted=0 GROUP BY 3,4
UNION ALL SELECT 'doc_sums','Act', YEAR(h.actdate), h.taxtype, COUNT(*), SUM(h.subtotal), SUM(h.pre_tax_total), SUM(h.total), NULL
FROM vtiger_sp_act h JOIN vtiger_crmentity c ON c.crmid=h.actid AND c.deleted=0 GROUP BY 3,4
UNION ALL SELECT 'doc_sums','Quotes', YEAR(c.createdtime), h.taxtype, COUNT(*), SUM(h.subtotal), SUM(h.pre_tax_total), SUM(h.total), NULL
FROM vtiger_quotes h JOIN vtiger_crmentity c ON c.crmid=h.quoteid AND c.deleted=0 GROUP BY 3,4
UNION ALL SELECT 'doc_sums','SalesOrder', YEAR(c.createdtime), h.taxtype, COUNT(*), SUM(h.subtotal), SUM(h.pre_tax_total), SUM(h.total), NULL
FROM vtiger_salesorder h JOIN vtiger_crmentity c ON c.crmid=h.salesorderid AND c.deleted=0 GROUP BY 3,4;
SELECT 'line_sums' k, c.setype, COUNT(*) n, SUM(i.quantity) qty, SUM(i.quantity*i.listprice) gross, SUM(IFNULL(i.discount_amount,0)) disc, SUM(i.margin) margin
FROM vtiger_inventoryproductrel i JOIN vtiger_crmentity c ON c.crmid=i.id AND c.deleted=0 GROUP BY 2;
SELECT 'payment_sums' k, YEAR(p.pay_date) y, p.pay_type, p.spstatus, COUNT(*) n, SUM(p.amount) amount
FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0 GROUP BY 2,3,4;
-- D-11 allocation (related_to first, Invoice<->payment link only when related_to is empty): sums by target and by document status.
WITH rel AS (
  SELECT DISTINCT x.payid, x.invoiceid FROM (
    SELECT r.relcrmid payid, r.crmid invoiceid FROM vtiger_crmentityrel r UNION ALL SELECT r.crmid, r.relcrmid FROM vtiger_crmentityrel r) x
  JOIN vtiger_crmentity ci ON ci.crmid=x.invoiceid AND ci.deleted=0 AND ci.setype='Invoice'
  JOIN vtiger_crmentity cp ON cp.crmid=x.payid AND cp.deleted=0 AND cp.setype='SPPayments'),
a AS (
  SELECT p.payid, p.amount, p.pay_type, IFNULL(p.spstatus,'') spstatus,
    CASE WHEN rc.setype IN ('Invoice','SalesOrder') AND rc.deleted=0 THEN p.related_to ELSE (SELECT MIN(rel.invoiceid) FROM rel WHERE rel.payid=p.payid) END target
  FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0 LEFT JOIN vtiger_crmentity rc ON rc.crmid=p.related_to)
SELECT 'alloc_sums' k, IFNULL(tc.setype,'(none)') target_type, a.pay_type, a.spstatus, COUNT(*) n, SUM(a.amount) amount
FROM a LEFT JOIN vtiger_crmentity tc ON tc.crmid=a.target GROUP BY 2,3,4 ORDER BY 2,3,4;
WITH rel AS (
  SELECT DISTINCT x.payid, x.invoiceid FROM (
    SELECT r.relcrmid payid, r.crmid invoiceid FROM vtiger_crmentityrel r UNION ALL SELECT r.crmid, r.relcrmid FROM vtiger_crmentityrel r) x
  JOIN vtiger_crmentity ci ON ci.crmid=x.invoiceid AND ci.deleted=0 AND ci.setype='Invoice'
  JOIN vtiger_crmentity cp ON cp.crmid=x.payid AND cp.deleted=0 AND cp.setype='SPPayments'),
a AS (
  SELECT p.amount, p.pay_type, p.spstatus,
    CASE WHEN rc.setype IN ('Invoice','SalesOrder') AND rc.deleted=0 THEN p.related_to ELSE (SELECT MIN(rel.invoiceid) FROM rel WHERE rel.payid=p.payid) END target
  FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0 LEFT JOIN vtiger_crmentity rc ON rc.crmid=p.related_to),
s AS (SELECT target id, SUM(amount) paid FROM a WHERE pay_type='Приход' AND spstatus='Executed' AND target IS NOT NULL GROUP BY target)
SELECT 'coverage_sums' k, c.setype m, IFNULL(h.st,'') st, COUNT(*) n, SUM(h.total) total, IFNULL(SUM(s.paid),0) paid
FROM (SELECT invoiceid id, invoicestatus st, total FROM vtiger_invoice UNION ALL SELECT salesorderid, sostatus, total FROM vtiger_salesorder) h
JOIN vtiger_crmentity c ON c.crmid=h.id AND c.deleted=0 LEFT JOIN s ON s.id=h.id GROUP BY 2,3 ORDER BY 2,3;
