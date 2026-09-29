-- Payment allocation semantics (aggregates only).
SET @eps := 0.005;
SELECT 'pay_link_shape' k, p.pay_type, p.spstatus, IFNULL(rc.setype,'(none)') related_setype, COUNT(*) n, SUM(p.amount<0) negative, SUM(p.amount=0) zero,
  SUM(p.amount<>ROUND(p.amount,2)) gt2dp, MIN(p.pay_date) first_date, MAX(p.pay_date) last_date
FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0 LEFT JOIN vtiger_crmentity rc ON rc.crmid=p.related_to
GROUP BY 2,3,4 ORDER BY 2,3,4;
-- related_to vs crmentityrel: see 33_allocation_check.sql (strict partition of live payments).
-- Payments per invoice (by related_to, executed incoming only).
WITH s AS (SELECT p.related_to id, COUNT(*) npay, SUM(p.amount) paid FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0
           WHERE p.pay_type='Приход' AND p.spstatus='Executed' GROUP BY p.related_to)
SELECT 'invoice_coverage' k, h.invoicestatus,
  SUM(s.id IS NULL) no_payment, SUM(s.npay=1) one_payment, SUM(s.npay>1) many_payments,
  SUM(ABS(IFNULL(s.paid,0)-h.total)<@eps) paid_eq_total, SUM(IFNULL(s.paid,0)>0 AND IFNULL(s.paid,0)<h.total-@eps) partial, SUM(IFNULL(s.paid,0)>h.total+@eps) overpaid,
  SUM(ABS(h.balance-(h.total-IFNULL(s.paid,0)))<@eps) balance_eq_total_minus_paid, COUNT(*) n
FROM vtiger_invoice h JOIN vtiger_crmentity c ON c.crmid=h.invoiceid AND c.deleted=0 LEFT JOIN s ON s.id=h.invoiceid GROUP BY 2 ORDER BY 2;
-- Payments whose amount relation to invoice: status mix.
SELECT 'payer_vs_invoice_account' k, SUM(p.payer=i.accountid) same_account, SUM(p.payer<>i.accountid) diff_account, SUM(p.payer IS NULL OR p.payer=0) no_payer, COUNT(*) n
FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0 JOIN vtiger_invoice i ON i.invoiceid=p.related_to;
SELECT 'payment_fields' k, SUM(doc_no IS NOT NULL AND doc_no<>0) doc_no_nz, SUM(pay_details<>'') details_nz, SUM(debit<>'') debit_nz, SUM(coracc_subacc<>'') coracc_nz,
  SUM(analytics_code<>'') analytics_nz, SUM(target_code<>'') target_nz, COUNT(DISTINCT pay_no) distinct_no, COUNT(*) n
FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0;
-- Numbering formats of LIVE documents (pattern only, digits replaced).
SELECT 'numbering' k, 'Invoice' m, REGEXP_REPLACE(h.invoice_no,'[0-9]','9') pattern, COUNT(*) n, COUNT(DISTINCT h.invoice_no) distinct_n FROM vtiger_invoice h JOIN vtiger_crmentity c ON c.crmid=h.invoiceid AND c.deleted=0 GROUP BY 3
UNION ALL SELECT 'numbering','Act', REGEXP_REPLACE(h.act_no,'[0-9]','9'), COUNT(*), COUNT(DISTINCT h.act_no) FROM vtiger_sp_act h JOIN vtiger_crmentity c ON c.crmid=h.actid AND c.deleted=0 GROUP BY 3
UNION ALL SELECT 'numbering','Quotes', REGEXP_REPLACE(h.quote_no,'[0-9]','9'), COUNT(*), COUNT(DISTINCT h.quote_no) FROM vtiger_quotes h JOIN vtiger_crmentity c ON c.crmid=h.quoteid AND c.deleted=0 GROUP BY 3
UNION ALL SELECT 'numbering','SalesOrder', REGEXP_REPLACE(h.salesorder_no,'[0-9]','9'), COUNT(*), COUNT(DISTINCT h.salesorder_no) FROM vtiger_salesorder h JOIN vtiger_crmentity c ON c.crmid=h.salesorderid AND c.deleted=0 GROUP BY 3
UNION ALL SELECT 'numbering','SPPayments', REGEXP_REPLACE(h.pay_no,'[0-9]','9'), COUNT(*), COUNT(DISTINCT h.pay_no) FROM sp_payments h JOIN vtiger_crmentity c ON c.crmid=h.payid AND c.deleted=0 GROUP BY 3
UNION ALL SELECT 'numbering','Consignment', REGEXP_REPLACE(h.consignment_no,'[0-9]','9'), COUNT(*), COUNT(DISTINCT h.consignment_no) FROM vtiger_sp_consignment h JOIN vtiger_crmentity c ON c.crmid=h.consignmentid AND c.deleted=0 GROUP BY 3;
SELECT 'numbering_empty' k, c.setype, c.deleted, COUNT(*) n FROM (
  SELECT invoiceid id FROM vtiger_invoice WHERE invoice_no IS NULL OR invoice_no='' UNION ALL SELECT actid FROM vtiger_sp_act WHERE act_no IS NULL OR act_no='') e
  JOIN vtiger_crmentity c ON c.crmid=e.id GROUP BY 2,3;
SELECT 'act_duplicate_numbers_live' k, COUNT(*) dup_numbers, IFNULL(SUM(cnt),0) acts FROM (SELECT h.act_no, COUNT(*) cnt FROM vtiger_sp_act h
  JOIN vtiger_crmentity c ON c.crmid=h.actid AND c.deleted=0 WHERE h.act_no<>'' GROUP BY h.act_no HAVING COUNT(*)>1) x;
SELECT 'modentity_num' k, semodule, prefix, start_id, cur_id, active FROM vtiger_modentity_num WHERE active=1 ORDER BY semodule;
-- Invoice -> Act cardinality.
SELECT 'invoice_act' k, COUNT(DISTINCT i.sp_act_id) acts_referenced, SUM(x.cnt>1) acts_with_many_invoices_rows, MAX(x.cnt) max_invoices_per_act
FROM vtiger_invoice i JOIN vtiger_crmentity c ON c.crmid=i.invoiceid AND c.deleted=0
JOIN (SELECT sp_act_id, COUNT(*) cnt FROM vtiger_invoice ii JOIN vtiger_crmentity cc ON cc.crmid=ii.invoiceid AND cc.deleted=0 WHERE sp_act_id IS NOT NULL AND sp_act_id<>0 GROUP BY sp_act_id) x ON x.sp_act_id=i.sp_act_id;
SELECT 'act_without_invoice' k, COUNT(*) n FROM vtiger_sp_act a JOIN vtiger_crmentity c ON c.crmid=a.actid AND c.deleted=0
WHERE NOT EXISTS (SELECT 1 FROM vtiger_invoice i JOIN vtiger_crmentity ci ON ci.crmid=i.invoiceid AND ci.deleted=0 WHERE i.sp_act_id=a.actid);
SELECT 'act_vs_invoice_totals' k, SUM(ABS(a.total-i.total)<@eps) same_total, SUM(ABS(a.total-i.total)>=@eps) diff_total, SUM(a.accountid=i.accountid) same_account, SUM(a.spcompany=i.spcompany) same_company, COUNT(*) n
FROM vtiger_invoice i JOIN vtiger_crmentity c ON c.crmid=i.invoiceid AND c.deleted=0 JOIN vtiger_sp_act a ON a.actid=i.sp_act_id;
SELECT 'so_recurring' k, r.recurring_frequency, r.start_period, r.end_period, r.last_recurring_date, r.payment_duration, r.invoice_status, s.enable_recurring, cs.deleted
FROM vtiger_invoice_recurring_info r JOIN vtiger_salesorder s ON s.salesorderid=r.salesorderid JOIN vtiger_crmentity cs ON cs.crmid=s.salesorderid;
SELECT 'invoices_from_so' k, YEAR(c.createdtime) y, COUNT(*) n FROM vtiger_invoice i JOIN vtiger_crmentity c ON c.crmid=i.invoiceid AND c.deleted=0 WHERE i.salesorderid IS NOT NULL AND i.salesorderid<>0 GROUP BY 2;
