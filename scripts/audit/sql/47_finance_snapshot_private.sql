-- PRIVATE OUTPUT: numeric snapshot of live finance documents, lines and payments for the stage 04.1 calculation core tests.
-- Only ids, amounts, tax regimes, statuses and years: no names, subjects, comments, addresses or bank details. Keep outside Git.
SELECT 'doc' k, 'Invoice' m, h.invoiceid id, h.taxtype, IFNULL(CAST(h.region_id AS CHAR),'null') region, IFNULL(h.spcompany,'(null)') spcompany,
  IFNULL(h.invoicestatus,'') status, IFNULL(YEAR(h.invoicedate),'null') y, h.subtotal, h.pre_tax_total, h.total, h.discount_amount, h.discount_percent,
  h.s_h_amount, h.s_h_percent, h.adjustment, h.balance, h.received, IFNULL(h.sp_act_id,0) act_id, IFNULL(h.salesorderid,0) so_id
FROM vtiger_invoice h JOIN vtiger_crmentity c ON c.crmid=h.invoiceid AND c.deleted=0
UNION ALL SELECT 'doc', 'Act', h.actid, h.taxtype, IFNULL(CAST(h.region_id AS CHAR),'null'), IFNULL(h.spcompany,'(null)'), IFNULL(h.sp_actstatus,''),
  IFNULL(YEAR(h.actdate),'null'), h.subtotal, h.pre_tax_total, h.total, h.discount_amount, h.discount_percent, h.s_h_amount, h.s_h_percent, h.adjustment,
  NULL, NULL, 0, IFNULL(h.salesorderid,0)
FROM vtiger_sp_act h JOIN vtiger_crmentity c ON c.crmid=h.actid AND c.deleted=0
UNION ALL SELECT 'doc', 'Quotes', h.quoteid, h.taxtype, IFNULL(CAST(h.region_id AS CHAR),'null'), IFNULL(h.spcompany,'(null)'), IFNULL(h.quotestage,''),
  YEAR(c.createdtime), h.subtotal, h.pre_tax_total, h.total, h.discount_amount, h.discount_percent, h.s_h_amount, h.s_h_percent, h.adjustment, NULL, NULL, 0, 0
FROM vtiger_quotes h JOIN vtiger_crmentity c ON c.crmid=h.quoteid AND c.deleted=0
UNION ALL SELECT 'doc', 'SalesOrder', h.salesorderid, h.taxtype, IFNULL(CAST(h.region_id AS CHAR),'null'), IFNULL(h.spcompany,'(null)'), IFNULL(h.sostatus,''),
  YEAR(c.createdtime), h.subtotal, h.pre_tax_total, h.total, h.discount_amount, h.discount_percent, h.s_h_amount, h.s_h_percent, h.adjustment, NULL, NULL, 0, 0
FROM vtiger_salesorder h JOIN vtiger_crmentity c ON c.crmid=h.salesorderid AND c.deleted=0;
SELECT 'line' k, c.setype m, i.id, i.lineitem_id, i.sequence_no, i.quantity, i.listprice, i.discount_amount, i.discount_percent, i.tax1, i.tax2, i.tax3,
  i.purchase_cost, i.margin, IFNULL(pc.setype,'') product_type
FROM vtiger_inventoryproductrel i JOIN vtiger_crmentity c ON c.crmid=i.id AND c.deleted=0 LEFT JOIN vtiger_crmentity pc ON pc.crmid=i.productid
WHERE c.setype IN ('Invoice','Act','Quotes','SalesOrder') ORDER BY i.id, i.sequence_no;
SELECT 'pay' k, p.payid, p.pay_type, IFNULL(p.spstatus,'') status, p.amount, IFNULL(p.related_to,0) related_to, IFNULL(rc.setype,'') related_type,
  IFNULL(CAST(rc.deleted AS CHAR),'') related_deleted, IFNULL(YEAR(p.pay_date),'null') y, IFNULL(p.spcompany,'(null)') spcompany
FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0 LEFT JOIN vtiger_crmentity rc ON rc.crmid=p.related_to ORDER BY p.payid;
SELECT DISTINCT 'rel' k, x.payid, x.invoiceid FROM (
  SELECT r.relcrmid payid, r.crmid invoiceid FROM vtiger_crmentityrel r UNION ALL SELECT r.crmid, r.relcrmid FROM vtiger_crmentityrel r) x
JOIN vtiger_crmentity ci ON ci.crmid=x.invoiceid AND ci.deleted=0 AND ci.setype='Invoice'
JOIN vtiger_crmentity cp ON cp.crmid=x.payid AND cp.deleted=0 AND cp.setype='SPPayments' ORDER BY 2,3;
