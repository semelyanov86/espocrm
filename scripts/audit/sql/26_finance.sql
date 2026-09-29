-- Recompute document totals from line items; returns only match counts and max deviations.
-- Formula hypotheses (Vtiger 7.1 + SalesPlatform): line_net = qty*price - line_discount;
-- individual: subtotal = SUM(line_net*(1+tax%)); group: subtotal = SUM(line_net); total = subtotal - hdr_discount + s_h + adjustment (+group tax).
SET @eps := 0.005;
WITH li AS (
  SELECT i.id, SUM(i.quantity*i.listprice - IFNULL(i.discount_amount,0) - i.quantity*i.listprice*IFNULL(i.discount_percent,0)/100) net,
         SUM((i.quantity*i.listprice - IFNULL(i.discount_amount,0) - i.quantity*i.listprice*IFNULL(i.discount_percent,0)/100)*(IFNULL(i.tax1,0)+IFNULL(i.tax2,0)+IFNULL(i.tax3,0))/100) tax,
         COUNT(*) nlines
  FROM vtiger_inventoryproductrel i GROUP BY i.id),
d AS (
  SELECT h.invoiceid id, h.taxtype, h.subtotal, h.total, h.pre_tax_total, IFNULL(h.discount_amount,0)+h.subtotal*IFNULL(h.discount_percent,0)/100 hdisc,
         IFNULL(h.s_h_amount,0) sh, IFNULL(h.adjustment,0) adj, l.net, l.tax, l.nlines
  FROM vtiger_invoice h JOIN vtiger_crmentity c ON c.crmid=h.invoiceid AND c.deleted=0 LEFT JOIN li l ON l.id=h.invoiceid)
SELECT 'Invoice' module, taxtype, COUNT(*) n, SUM(nlines IS NULL) no_lines,
  SUM(ABS(subtotal - IF(taxtype='individual', net+tax, net)) < @eps) subtotal_ok,
  ROUND(MAX(ABS(subtotal - IF(taxtype='individual', net+tax, net))),4) subtotal_maxdiff,
  SUM(ABS(pre_tax_total - (net - hdisc + sh)) < @eps) pretax_ok, ROUND(MAX(ABS(pre_tax_total - (net - hdisc + sh))),4) pretax_maxdiff,
  SUM(ABS(total - (subtotal - hdisc + sh + adj)) < @eps) total_eq_sub_ok, ROUND(MAX(ABS(total - (subtotal - hdisc + sh + adj))),4) total_eq_sub_maxdiff,
  SUM(ABS(total - (net + tax - hdisc + sh + adj)) < @eps) total_net_tax_ok,
  SUM(ABS(total - ROUND(total,2)) > 0) total_gt_2dp, SUM(ABS(subtotal - ROUND(subtotal,2)) > 0) subtotal_gt_2dp
FROM d GROUP BY taxtype;
WITH li AS (
  SELECT i.id, SUM(i.quantity*i.listprice - IFNULL(i.discount_amount,0) - i.quantity*i.listprice*IFNULL(i.discount_percent,0)/100) net,
         SUM((i.quantity*i.listprice - IFNULL(i.discount_amount,0) - i.quantity*i.listprice*IFNULL(i.discount_percent,0)/100)*(IFNULL(i.tax1,0)+IFNULL(i.tax2,0)+IFNULL(i.tax3,0))/100) tax,
         COUNT(*) nlines
  FROM vtiger_inventoryproductrel i GROUP BY i.id),
d AS (
  SELECT h.actid id, h.taxtype, h.subtotal, h.total, h.pre_tax_total, IFNULL(h.discount_amount,0)+h.subtotal*IFNULL(h.discount_percent,0)/100 hdisc,
         IFNULL(h.s_h_amount,0) sh, IFNULL(h.adjustment,0) adj, l.net, l.tax, l.nlines
  FROM vtiger_sp_act h JOIN vtiger_crmentity c ON c.crmid=h.actid AND c.deleted=0 LEFT JOIN li l ON l.id=h.actid)
SELECT 'Act' module, taxtype, COUNT(*) n, SUM(nlines IS NULL) no_lines,
  SUM(ABS(subtotal - IF(taxtype='individual', net+tax, net)) < @eps) subtotal_ok,
  ROUND(MAX(ABS(subtotal - IF(taxtype='individual', net+tax, net))),4) subtotal_maxdiff,
  SUM(ABS(pre_tax_total - (net - hdisc + sh)) < @eps) pretax_ok, ROUND(MAX(ABS(pre_tax_total - (net - hdisc + sh))),4) pretax_maxdiff,
  SUM(ABS(total - (subtotal - hdisc + sh + adj)) < @eps) total_eq_sub_ok, ROUND(MAX(ABS(total - (subtotal - hdisc + sh + adj))),4) total_eq_sub_maxdiff,
  SUM(ABS(total - (net + tax - hdisc + sh + adj)) < @eps) total_net_tax_ok,
  SUM(ABS(total - ROUND(total,2)) > 0) total_gt_2dp, SUM(ABS(subtotal - ROUND(subtotal,2)) > 0) subtotal_gt_2dp
FROM d GROUP BY taxtype;
WITH li AS (
  SELECT i.id, SUM(i.quantity*i.listprice - IFNULL(i.discount_amount,0) - i.quantity*i.listprice*IFNULL(i.discount_percent,0)/100) net,
         SUM((i.quantity*i.listprice - IFNULL(i.discount_amount,0) - i.quantity*i.listprice*IFNULL(i.discount_percent,0)/100)*(IFNULL(i.tax1,0)+IFNULL(i.tax2,0)+IFNULL(i.tax3,0))/100) tax,
         COUNT(*) nlines
  FROM vtiger_inventoryproductrel i GROUP BY i.id),
d AS (
  SELECT h.quoteid id, h.taxtype, h.subtotal, h.total, h.pre_tax_total, IFNULL(h.discount_amount,0)+h.subtotal*IFNULL(h.discount_percent,0)/100 hdisc,
         IFNULL(h.s_h_amount,0) sh, IFNULL(h.adjustment,0) adj, l.net, l.tax, l.nlines
  FROM vtiger_quotes h JOIN vtiger_crmentity c ON c.crmid=h.quoteid AND c.deleted=0 LEFT JOIN li l ON l.id=h.quoteid)
SELECT 'Quotes' module, taxtype, COUNT(*) n, SUM(nlines IS NULL) no_lines,
  SUM(ABS(subtotal - IF(taxtype='individual', net+tax, net)) < @eps) subtotal_ok,
  ROUND(MAX(ABS(subtotal - IF(taxtype='individual', net+tax, net))),4) subtotal_maxdiff,
  SUM(ABS(pre_tax_total - (net - hdisc + sh)) < @eps) pretax_ok, ROUND(MAX(ABS(pre_tax_total - (net - hdisc + sh))),4) pretax_maxdiff,
  SUM(ABS(total - (subtotal - hdisc + sh + adj)) < @eps) total_eq_sub_ok, ROUND(MAX(ABS(total - (subtotal - hdisc + sh + adj))),4) total_eq_sub_maxdiff,
  SUM(ABS(total - (net + tax - hdisc + sh + adj)) < @eps) total_net_tax_ok,
  SUM(ABS(total - ROUND(total,2)) > 0) total_gt_2dp, SUM(ABS(subtotal - ROUND(subtotal,2)) > 0) subtotal_gt_2dp
FROM d GROUP BY taxtype;
WITH li AS (
  SELECT i.id, SUM(i.quantity*i.listprice - IFNULL(i.discount_amount,0) - i.quantity*i.listprice*IFNULL(i.discount_percent,0)/100) net,
         SUM((i.quantity*i.listprice - IFNULL(i.discount_amount,0) - i.quantity*i.listprice*IFNULL(i.discount_percent,0)/100)*(IFNULL(i.tax1,0)+IFNULL(i.tax2,0)+IFNULL(i.tax3,0))/100) tax,
         COUNT(*) nlines
  FROM vtiger_inventoryproductrel i GROUP BY i.id),
d AS (
  SELECT h.salesorderid id, h.taxtype, h.subtotal, h.total, h.pre_tax_total, IFNULL(h.discount_amount,0)+h.subtotal*IFNULL(h.discount_percent,0)/100 hdisc,
         IFNULL(h.s_h_amount,0) sh, IFNULL(h.adjustment,0) adj, l.net, l.tax, l.nlines
  FROM vtiger_salesorder h JOIN vtiger_crmentity c ON c.crmid=h.salesorderid AND c.deleted=0 LEFT JOIN li l ON l.id=h.salesorderid)
SELECT 'SalesOrder' module, taxtype, COUNT(*) n, SUM(nlines IS NULL) no_lines,
  SUM(ABS(subtotal - IF(taxtype='individual', net+tax, net)) < @eps) subtotal_ok,
  ROUND(MAX(ABS(subtotal - IF(taxtype='individual', net+tax, net))),4) subtotal_maxdiff,
  SUM(ABS(pre_tax_total - (net - hdisc + sh)) < @eps) pretax_ok, ROUND(MAX(ABS(pre_tax_total - (net - hdisc + sh))),4) pretax_maxdiff,
  SUM(ABS(total - (subtotal - hdisc + sh + adj)) < @eps) total_eq_sub_ok, ROUND(MAX(ABS(total - (subtotal - hdisc + sh + adj))),4) total_eq_sub_maxdiff,
  SUM(ABS(total - (net + tax - hdisc + sh + adj)) < @eps) total_net_tax_ok,
  SUM(ABS(total - ROUND(total,2)) > 0) total_gt_2dp, SUM(ABS(subtotal - ROUND(subtotal,2)) > 0) subtotal_gt_2dp
FROM d GROUP BY taxtype;
WITH li AS (
  SELECT i.id, SUM(i.quantity*i.listprice - IFNULL(i.discount_amount,0) - i.quantity*i.listprice*IFNULL(i.discount_percent,0)/100) net,
         SUM((i.quantity*i.listprice - IFNULL(i.discount_amount,0) - i.quantity*i.listprice*IFNULL(i.discount_percent,0)/100)*(IFNULL(i.tax1,0)+IFNULL(i.tax2,0)+IFNULL(i.tax3,0))/100) tax,
         COUNT(*) nlines
  FROM vtiger_inventoryproductrel i GROUP BY i.id),
d AS (
  SELECT h.consignmentid id, h.taxtype, h.subtotal, h.total, h.pre_tax_total, IFNULL(h.discount_amount,0)+h.subtotal*IFNULL(h.discount_percent,0)/100 hdisc,
         IFNULL(h.s_h_amount,0) sh, IFNULL(h.adjustment,0) adj, l.net, l.tax, l.nlines
  FROM vtiger_sp_consignment h JOIN vtiger_crmentity c ON c.crmid=h.consignmentid AND c.deleted=0 LEFT JOIN li l ON l.id=h.consignmentid)
SELECT 'Consignment' module, taxtype, COUNT(*) n, SUM(nlines IS NULL) no_lines,
  SUM(ABS(subtotal - IF(taxtype='individual', net+tax, net)) < @eps) subtotal_ok,
  ROUND(MAX(ABS(subtotal - IF(taxtype='individual', net+tax, net))),4) subtotal_maxdiff,
  SUM(ABS(pre_tax_total - (net - hdisc + sh)) < @eps) pretax_ok, ROUND(MAX(ABS(pre_tax_total - (net - hdisc + sh))),4) pretax_maxdiff,
  SUM(ABS(total - (subtotal - hdisc + sh + adj)) < @eps) total_eq_sub_ok, ROUND(MAX(ABS(total - (subtotal - hdisc + sh + adj))),4) total_eq_sub_maxdiff,
  SUM(ABS(total - (net + tax - hdisc + sh + adj)) < @eps) total_net_tax_ok,
  SUM(ABS(total - ROUND(total,2)) > 0) total_gt_2dp, SUM(ABS(subtotal - ROUND(subtotal,2)) > 0) subtotal_gt_2dp
FROM d GROUP BY taxtype;
SELECT 'invoice_balance' k, COUNT(*) n, SUM(ABS(balance-total)<@eps) balance_eq_total, SUM(ABS(balance-(total-received))<@eps) balance_eq_total_minus_received, SUM(received<>0) received_nz
FROM vtiger_invoice h JOIN vtiger_crmentity c ON c.crmid=h.invoiceid AND c.deleted=0;
-- VTEItems vs inventory lines for the same parent record.
WITH v AS (SELECT related_to id, COUNT(*) n, SUM(quantity*listprice) gross FROM vtiger_vteitems t JOIN vtiger_crmentity c ON c.crmid=t.vteitemid AND c.deleted=0 GROUP BY related_to),
l AS (SELECT id, COUNT(*) n, SUM(quantity*listprice) gross FROM vtiger_inventoryproductrel GROUP BY id)
SELECT 'vteitems_vs_lines' k, COUNT(*) parents, SUM(l.id IS NULL) parent_without_lines, SUM(v.n=l.n) same_count, SUM(ABS(v.gross-l.gross)<0.005) same_gross, MIN(pc.createdtime) parent_min_created, MAX(pc.createdtime) parent_max_created
FROM v LEFT JOIN l ON l.id=v.id LEFT JOIN vtiger_crmentity pc ON pc.crmid=v.id;
SELECT 'lines_without_vteitems' k, c.setype, COUNT(DISTINCT l.id) parents, SUM(c.createdtime>'2018-11-02 14:46:02') parents_created_after_vte_import
FROM vtiger_inventoryproductrel l JOIN vtiger_crmentity c ON c.crmid=l.id AND c.deleted=0 LEFT JOIN vtiger_vteitems v ON v.related_to=l.id WHERE v.vteitemid IS NULL GROUP BY 2;
