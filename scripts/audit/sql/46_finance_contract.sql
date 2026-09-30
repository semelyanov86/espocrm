-- Stage 04.1: facts behind the finance contract (aggregates only; spcompany values are configuration, not personal data).
SET @eps := 0.005;

-- 1. Legal entity: which spcompany values each module stores, in which period, next to which tax regime.
WITH d AS (
  SELECT 'Invoice' m, h.spcompany v, h.region_id r, c.createdtime t FROM vtiger_invoice h JOIN vtiger_crmentity c ON c.crmid=h.invoiceid AND c.deleted=0
  UNION ALL SELECT 'Act', h.spcompany, h.region_id, c.createdtime FROM vtiger_sp_act h JOIN vtiger_crmentity c ON c.crmid=h.actid AND c.deleted=0
  UNION ALL SELECT 'Quotes', h.spcompany, h.region_id, c.createdtime FROM vtiger_quotes h JOIN vtiger_crmentity c ON c.crmid=h.quoteid AND c.deleted=0
  UNION ALL SELECT 'SalesOrder', h.spcompany, h.region_id, c.createdtime FROM vtiger_salesorder h JOIN vtiger_crmentity c ON c.crmid=h.salesorderid AND c.deleted=0
  UNION ALL SELECT 'Consignment', h.spcompany, h.region_id, c.createdtime FROM vtiger_sp_consignment h JOIN vtiger_crmentity c ON c.crmid=h.consignmentid AND c.deleted=0
  UNION ALL SELECT 'SPPayments', h.spcompany, NULL, c.createdtime FROM sp_payments h JOIN vtiger_crmentity c ON c.crmid=h.payid AND c.deleted=0
  UNION ALL SELECT 'Potentials', h.spcompany, NULL, c.createdtime FROM vtiger_potential h JOIN vtiger_crmentity c ON c.crmid=h.potentialid AND c.deleted=0)
SELECT 'spcompany_usage' k, m,
  CASE WHEN v IS NULL THEN '(null)' WHEN v='' THEN '(empty)' WHEN v IN ('Default','По умолчанию') THEN v ELSE '(other)' END val,
  CASE WHEN r IS NULL THEN 'null' ELSE CAST(r AS CHAR) END region, COUNT(*) n, DATE(MIN(t)) first_created, DATE(MAX(t)) last_created
FROM d GROUP BY 2,3,4 ORDER BY 2,3,4;
-- Numbering counters per legal entity (SalesPlatform keeps a counter per spcompany; 'Default' is stored as '').
SELECT 'modentity_num_company' k, semodule, prefix, cur_id, active, CASE WHEN spcompany IS NULL THEN '(null)' WHEN spcompany='' THEN '(empty)' ELSE spcompany END spcompany
FROM vtiger_modentity_num WHERE semodule IN ('Invoice','Act','Quotes','SalesOrder','SPPayments','Consignment') ORDER BY semodule, num_id;
-- Change history of the field: transitions between the two strings.
SELECT 'spcompany_history' k, b.module,
  CASE WHEN d.prevalue IS NULL THEN '(null)' WHEN d.prevalue='' THEN '(empty)' WHEN d.prevalue IN ('Default','По умолчанию') THEN d.prevalue ELSE '(other)' END prev,
  CASE WHEN d.postvalue IS NULL THEN '(null)' WHEN d.postvalue='' THEN '(empty)' WHEN d.postvalue IN ('Default','По умолчанию') THEN d.postvalue ELSE '(other)' END post,
  b.status, COUNT(*) n, DATE(MIN(b.changedon)) first_on, DATE(MAX(b.changedon)) last_on
FROM vtiger_modtracker_detail d JOIN vtiger_modtracker_basic b ON b.id=d.id WHERE d.fieldname='spcompany' GROUP BY 2,3,4,5 ORDER BY 2,3,4,5;
SELECT 'orgdetails_company' k, IFNULL(company,'(null)') company, COUNT(*) n FROM vtiger_organizationdetails GROUP BY 2;
SELECT 'pdf_templates_company' k, module, IFNULL(spcompany,'(null)') spcompany, COUNT(*) n FROM sp_templates GROUP BY 2,3 ORDER BY 2,3;

-- 2. Header shapes of live documents.
WITH h AS (
  SELECT 'Invoice' m, i.invoicestatus st, i.taxtype, i.region_id, i.currency_id, i.conversion_rate, i.subtotal, i.pre_tax_total, i.total, i.discount_amount, i.discount_percent,
         i.s_h_amount, i.s_h_percent, i.adjustment, i.invoicedate d1 FROM vtiger_invoice i JOIN vtiger_crmentity c ON c.crmid=i.invoiceid AND c.deleted=0
  UNION ALL SELECT 'Act', a.sp_actstatus, a.taxtype, a.region_id, a.currency_id, a.conversion_rate, a.subtotal, a.pre_tax_total, a.total, a.discount_amount, a.discount_percent,
         a.s_h_amount, a.s_h_percent, a.adjustment, a.actdate FROM vtiger_sp_act a JOIN vtiger_crmentity c ON c.crmid=a.actid AND c.deleted=0
  UNION ALL SELECT 'Quotes', q.quotestage, q.taxtype, q.region_id, q.currency_id, q.conversion_rate, q.subtotal, q.pre_tax_total, q.total, q.discount_amount, q.discount_percent,
         q.s_h_amount, q.s_h_percent, q.adjustment, DATE(c.createdtime) FROM vtiger_quotes q JOIN vtiger_crmentity c ON c.crmid=q.quoteid AND c.deleted=0
  UNION ALL SELECT 'SalesOrder', s.sostatus, s.taxtype, s.region_id, s.currency_id, s.conversion_rate, s.subtotal, s.pre_tax_total, s.total, s.discount_amount, s.discount_percent,
         s.s_h_amount, s.s_h_percent, s.adjustment, DATE(c.createdtime) FROM vtiger_salesorder s JOIN vtiger_crmentity c ON c.crmid=s.salesorderid AND c.deleted=0)
SELECT 'header_shape' k, m, COUNT(*) n,
  SUM(subtotal IS NULL) sub_null, SUM(pre_tax_total IS NULL) pre_null, SUM(total IS NULL) total_null, SUM(total<0) total_neg, SUM(total=0) total_zero,
  SUM(discount_amount IS NULL) damt_null, SUM(discount_amount<>0) damt_nz, SUM(discount_percent IS NULL) dpct_null, SUM(discount_percent<>0) dpct_nz,
  SUM(discount_amount<>0 AND discount_percent<>0) both_disc, SUM(s_h_amount IS NULL) sh_null, SUM(s_h_amount<>0) sh_nz, SUM(s_h_percent<>0) shp_nz,
  SUM(adjustment IS NULL) adj_null, SUM(adjustment<>0) adj_nz, GROUP_CONCAT(DISTINCT currency_id) currencies, GROUP_CONCAT(DISTINCT conversion_rate) rates,
  SUM(region_id IS NULL) region_null, SUM(region_id=0) region_0, SUM(region_id>0) region_other, MIN(CASE WHEN region_id=0 THEN d1 END) region0_first,
  MAX(CASE WHEN region_id IS NULL THEN d1 END) region_null_last, SUM(d1 IS NULL) date_null,
  SUM(total<>ROUND(total,2) OR subtotal<>ROUND(subtotal,2) OR pre_tax_total<>ROUND(pre_tax_total,2) OR IFNULL(discount_amount,0)<>ROUND(IFNULL(discount_amount,0),2)) gt2dp
FROM h GROUP BY m ORDER BY m;
SELECT 'invoice_status_sign' k, IFNULL(invoicestatus,'(null)') st, COUNT(*) n, SUM(total<0) neg, SUM(total=0) zero
FROM vtiger_invoice i JOIN vtiger_crmentity c ON c.crmid=i.invoiceid AND c.deleted=0 GROUP BY 2 ORDER BY 2;
-- Group tax: the rate stored on every line and the tax amount = grand total - pre-tax total.
WITH g AS (SELECT id, MIN(tax1) tmin, MAX(tax1) tmax, SUM(tax2<>0 OR tax3<>0) other_tax FROM vtiger_inventoryproductrel GROUP BY id)
SELECT 'group_tax' k, COUNT(*) n, SUM(g.tmin=g.tmax) same_rate_all_lines, SUM(g.other_tax>0) with_tax2_tax3,
  SUM(ABS((h.total-h.pre_tax_total) - ROUND((h.subtotal-IFNULL(h.discount_amount,0))*g.tmax/100,2)) < @eps) tax_eq_base_x_rate,
  SUM(IFNULL(h.discount_amount,0)<>0 OR IFNULL(h.discount_percent,0)<>0) with_hdr_discount, SUM(h.s_h_amount<>0) with_sh, SUM(h.adjustment<>0) with_adj
FROM vtiger_invoice h JOIN vtiger_crmentity c ON c.crmid=h.invoiceid AND c.deleted=0 JOIN g ON g.id=h.invoiceid WHERE h.taxtype='group';

-- 3. Line shapes of live documents (net = qty*price - discount amount - qty*price*discount percent/100).
WITH hd AS (
  SELECT invoiceid id, region_id, taxtype FROM vtiger_invoice UNION ALL SELECT actid, region_id, taxtype FROM vtiger_sp_act
  UNION ALL SELECT quoteid, region_id, taxtype FROM vtiger_quotes UNION ALL SELECT salesorderid, region_id, taxtype FROM vtiger_salesorder),
l AS (
  SELECT c.setype m, i.*, hd.region_id, hd.taxtype,
         i.quantity*i.listprice - IFNULL(i.discount_amount,0) - i.quantity*i.listprice*IFNULL(i.discount_percent,0)/100 net
  FROM vtiger_inventoryproductrel i JOIN vtiger_crmentity c ON c.crmid=i.id AND c.deleted=0 JOIN hd ON hd.id=i.id)
SELECT 'line_shape' k, m, COUNT(*) n, SUM(quantity<=0) qty_le0, SUM(listprice<0) price_neg, SUM(listprice=0) price_zero, SUM(net<0) net_neg, SUM(net=0) net_zero,
  SUM(quantity<>ROUND(quantity,2)) qty_gt2dp, SUM(listprice<>ROUND(listprice,2)) price_gt2dp, SUM(IFNULL(discount_amount,0)<>ROUND(IFNULL(discount_amount,0),2)) damt_gt2dp,
  SUM(tax1 IS NULL) tax1_null, SUM(discount_amount IS NULL) damt_null, SUM(discount_percent IS NULL) dpct_null, SUM(purchase_cost IS NULL) pc_null, SUM(margin IS NULL) margin_null,
  SUM(ABS(margin-(net-IFNULL(purchase_cost,0))) < @eps) margin_eq_net_minus_cost, SUM(margin=0 AND net<>0) margin_zero_net_nz,
  SUM(margin=0 AND net<>0 AND region_id IS NULL) margin_zero_region_null, SUM(margin<>0 AND ABS(margin-(net-IFNULL(purchase_cost,0))) >= @eps) margin_other,
  SUM(tax1<>0 AND region_id=0) tax_on_region0, SUM(tax1<>0 AND region_id IS NULL) tax_on_region_null
FROM l GROUP BY m ORDER BY m;
WITH s AS (SELECT i.id, COUNT(*) cnt, MIN(sequence_no) mn, MAX(sequence_no) mx, COUNT(DISTINCT sequence_no) dcnt FROM vtiger_inventoryproductrel i GROUP BY i.id)
SELECT 'line_sequence' k, c.setype m, COUNT(*) docs, SUM(s.mn=1 AND s.mx=s.cnt AND s.dcnt=s.cnt) seq_1_to_n, MAX(s.cnt) max_lines,
  SUM(s.cnt=1) one_line, SUM(s.cnt=2) two_lines, SUM(s.cnt>2) more_lines
FROM s JOIN vtiger_crmentity c ON c.crmid=s.id AND c.deleted=0 GROUP BY 2 ORDER BY 2;
SELECT 'line_ids' k, COUNT(*) n, COUNT(DISTINCT lineitem_id) distinct_lineitem, SUM(lineitem_id IS NULL) lineitem_null FROM vtiger_inventoryproductrel;
SELECT 'line_product' k, c.setype m, IFNULL(pc.setype,'(missing)') product_type, IFNULL(pc.deleted,'') product_deleted, COUNT(*) n
FROM vtiger_inventoryproductrel i JOIN vtiger_crmentity c ON c.crmid=i.id AND c.deleted=0 LEFT JOIN vtiger_crmentity pc ON pc.crmid=i.productid
GROUP BY 2,3,4 ORDER BY 2,3,4;

-- 4. Payments: amount shape, links, payer types and D-11 allocation (related_to first, Invoice<->payment link only when related_to is empty).
--    Coverage counts incoming payments in status Executed or with an empty status (owner decision Q-37).
WITH rel AS (
  SELECT DISTINCT x.payid, x.invoiceid FROM (
    SELECT r.relcrmid payid, r.crmid invoiceid FROM vtiger_crmentityrel r UNION ALL SELECT r.crmid, r.relcrmid FROM vtiger_crmentityrel r) x
  JOIN vtiger_crmentity ci ON ci.crmid=x.invoiceid AND ci.deleted=0 AND ci.setype='Invoice'
  JOIN vtiger_crmentity cp ON cp.crmid=x.payid AND cp.deleted=0 AND cp.setype='SPPayments')
SELECT 'payment_shape' k, p.pay_type, IFNULL(p.spstatus,'(null)') st, COUNT(*) n, SUM(p.amount IS NULL) amt_null, SUM(p.amount=0) amt_zero, SUM(p.amount<0) amt_neg,
  SUM(p.amount<>ROUND(p.amount,2)) amt_gt2dp, SUM(IFNULL(p.related_to,0)<>0) with_related_to, SUM(EXISTS (SELECT 1 FROM rel WHERE rel.payid=p.payid)) with_rel,
  SUM(IFNULL(p.related_to,0)<>0 OR EXISTS (SELECT 1 FROM rel WHERE rel.payid=p.payid)) allocated
FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0 GROUP BY 2,3 ORDER BY 2,3;
SELECT 'payment_payer' k, p.pay_type, IFNULL(pc.setype,'(none)') payer_type, IFNULL(pc.deleted,'') payer_deleted, COUNT(*) n
FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0 LEFT JOIN vtiger_crmentity pc ON pc.crmid=p.payer GROUP BY 2,3,4 ORDER BY 2,3,4;
WITH rel AS (
  SELECT DISTINCT x.payid, x.invoiceid FROM (
    SELECT r.relcrmid payid, r.crmid invoiceid FROM vtiger_crmentityrel r UNION ALL SELECT r.crmid, r.relcrmid FROM vtiger_crmentityrel r) x
  JOIN vtiger_crmentity ci ON ci.crmid=x.invoiceid AND ci.deleted=0 AND ci.setype='Invoice'
  JOIN vtiger_crmentity cp ON cp.crmid=x.payid AND cp.deleted=0 AND cp.setype='SPPayments'),
a AS (
  SELECT p.payid, p.amount, p.pay_type, p.spstatus,
    CASE WHEN IFNULL(p.related_to,0)=0 THEN (SELECT MIN(rel.invoiceid) FROM rel WHERE rel.payid=p.payid)
         WHEN rc.setype IN ('Invoice','SalesOrder') AND rc.deleted=0 THEN p.related_to END target
  FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0 LEFT JOIN vtiger_crmentity rc ON rc.crmid=p.related_to),
s AS (SELECT target id, COUNT(*) npay, SUM(amount) paid FROM a WHERE pay_type='Приход' AND (spstatus='Executed' OR IFNULL(spstatus,'')='') AND target IS NOT NULL GROUP BY target)
SELECT 'coverage_d11' k, c.setype m, IFNULL(h.st,'(null)') st, COUNT(*) n, SUM(s.id IS NULL) no_payment, SUM(s.npay=1) one_payment, SUM(s.npay>1) many_payments,
  SUM(ABS(IFNULL(s.paid,0)-h.total) < @eps) paid_eq_total, SUM(IFNULL(s.paid,0)>0 AND IFNULL(s.paid,0) < h.total-@eps) partial, SUM(IFNULL(s.paid,0) > h.total+@eps) overpaid
FROM (SELECT invoiceid id, invoicestatus st, total FROM vtiger_invoice UNION ALL SELECT salesorderid, sostatus, total FROM vtiger_salesorder) h
JOIN vtiger_crmentity c ON c.crmid=h.id AND c.deleted=0 LEFT JOIN s ON s.id=h.id GROUP BY 2,3 ORDER BY 2,3;
WITH rel AS (
  SELECT DISTINCT x.payid, x.invoiceid FROM (
    SELECT r.relcrmid payid, r.crmid invoiceid FROM vtiger_crmentityrel r UNION ALL SELECT r.crmid, r.relcrmid FROM vtiger_crmentityrel r) x
  JOIN vtiger_crmentity ci ON ci.crmid=x.invoiceid AND ci.deleted=0 AND ci.setype='Invoice'
  JOIN vtiger_crmentity cp ON cp.crmid=x.payid AND cp.deleted=0 AND cp.setype='SPPayments')
SELECT 'allocated_by_status' k, p.pay_type, IFNULL(p.spstatus,'(null)') st, COUNT(*) n,
  SUM(IFNULL(p.related_to,0)<>0 OR EXISTS (SELECT 1 FROM rel WHERE rel.payid=p.payid)) allocated
FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0 GROUP BY 2,3 ORDER BY 2,3;

-- 5. Invoice -> Act: same tax regime and totals.
SELECT 'invoice_act_shape' k, COUNT(*) n, SUM(a.taxtype=i.taxtype) same_taxtype, SUM(ABS(a.total-i.total) < @eps) same_total,
  SUM(ABS(a.subtotal-i.subtotal) < @eps) same_subtotal, SUM(a.total > i.total + @eps) act_gt_invoice, SUM(a.total < i.total - @eps) act_lt_invoice
FROM vtiger_invoice i JOIN vtiger_crmentity c ON c.crmid=i.invoiceid AND c.deleted=0
JOIN vtiger_sp_act a ON a.actid=i.sp_act_id JOIN vtiger_crmentity ca ON ca.crmid=a.actid AND ca.deleted=0;

-- 6. Outgoing payments linked to invoices only through the related list (Q-36), incoming payments without a status (Q-37).
WITH rel AS (
  SELECT DISTINCT x.payid, x.invoiceid FROM (
    SELECT r.relcrmid payid, r.crmid invoiceid FROM vtiger_crmentityrel r UNION ALL SELECT r.crmid, r.relcrmid FROM vtiger_crmentityrel r) x
  JOIN vtiger_crmentity ci ON ci.crmid=x.invoiceid AND ci.deleted=0 AND ci.setype='Invoice'
  JOIN vtiger_crmentity cp ON cp.crmid=x.payid AND cp.deleted=0 AND cp.setype='SPPayments')
SELECT 'expense_rel' k, YEAR(p.pay_date) y, IFNULL(pc.setype,'(none)') payer_type, (cf.cf_1204 IS NOT NULL AND cf.cf_1204<>'') bank_import,
  i.invoicestatus, (i.accountid=p.payer) payer_is_invoice_account, COUNT(*) n, SUM(ABS(p.amount-i.total) < @eps) amount_eq_total
FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0 JOIN sp_paymentscf cf ON cf.payid=p.payid
JOIN rel ON rel.payid=p.payid JOIN vtiger_invoice i ON i.invoiceid=rel.invoiceid LEFT JOIN vtiger_crmentity pc ON pc.crmid=p.payer
WHERE p.pay_type='Expense' GROUP BY 2,3,4,5,6 ORDER BY 2,3,4,5,6;
SELECT 'empty_status_pay' k, p.pay_type, YEAR(p.pay_date) y, COUNT(*) n, SUM(IFNULL(p.related_to,0)<>0) with_related, SUM(i.invoicestatus='Paid') to_paid_invoice,
  SUM(p.amount=0) zero
FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0 LEFT JOIN vtiger_invoice i ON i.invoiceid=p.related_to
WHERE IFNULL(p.spstatus,'')='' GROUP BY 2,3 ORDER BY 2,3;
SELECT 'spstatus_picklist' k, spstatus, sortorderid FROM vtiger_spstatus ORDER BY sortorderid, spstatus;

-- 7. Numbers: ranges against the counters (cur_id is the next number) and number formats by legal entity after the 2018-07 upgrade.
SELECT 'number_range' k, 'Invoice С-' m, MIN(CAST(SUBSTRING(invoice_no,3) AS UNSIGNED)) mn, MAX(CAST(SUBSTRING(invoice_no,3) AS UNSIGNED)) mx, COUNT(DISTINCT invoice_no) n
FROM vtiger_invoice h JOIN vtiger_crmentity c ON c.crmid=h.invoiceid WHERE h.invoice_no LIKE 'С-%'
UNION ALL SELECT 'number_range', 'Act', MIN(CAST(act_no AS UNSIGNED)), MAX(CAST(act_no AS UNSIGNED)), COUNT(DISTINCT act_no)
FROM vtiger_sp_act h JOIN vtiger_crmentity c ON c.crmid=h.actid WHERE act_no<>''
UNION ALL SELECT 'number_range', 'SPPayments', MIN(CAST(pay_no AS UNSIGNED)), MAX(CAST(pay_no AS UNSIGNED)), COUNT(DISTINCT pay_no)
FROM sp_payments h JOIN vtiger_crmentity c ON c.crmid=h.payid;
SELECT 'number_by_company' k, 'Invoice' m, IFNULL(spcompany,'(null)') v, REGEXP_REPLACE(invoice_no,'[0-9]','9') pattern, COUNT(*) n
FROM vtiger_invoice h JOIN vtiger_crmentity c ON c.crmid=h.invoiceid AND c.deleted=0 WHERE c.createdtime>='2018-07-01' AND h.spcompany IN ('Default','По умолчанию') GROUP BY 3,4
UNION ALL SELECT 'number_by_company', 'Act', IFNULL(spcompany,'(null)'), REGEXP_REPLACE(act_no,'[0-9]','9'), COUNT(*)
FROM vtiger_sp_act h JOIN vtiger_crmentity c ON c.crmid=h.actid AND c.deleted=0 WHERE h.spcompany IN ('Default','По умолчанию') GROUP BY 3,4
ORDER BY 2,3,4;
