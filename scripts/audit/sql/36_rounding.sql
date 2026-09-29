-- Q-03: how Vtiger rounds document sums when line amounts have fractions of a kopeck (aggregates only).
SET @eps := 0.0000005;
WITH li AS (
  SELECT i.id,
    SUM(i.quantity*i.listprice - IFNULL(i.discount_amount,0)) net_exact,
    SUM(ROUND(i.quantity*i.listprice - IFNULL(i.discount_amount,0), 2)) net_line_rounded,
    SUM(ABS(i.quantity*i.listprice - ROUND(i.quantity*i.listprice, 2)) > @eps) frac_lines,
    COUNT(*) nlines
  FROM vtiger_inventoryproductrel i GROUP BY i.id),
d AS (
  SELECT c.setype, h.subtotal, h.total, l.* FROM (
    SELECT invoiceid did, subtotal, total FROM vtiger_invoice UNION ALL SELECT actid, subtotal, total FROM vtiger_sp_act
    UNION ALL SELECT quoteid, subtotal, total FROM vtiger_quotes UNION ALL SELECT salesorderid, subtotal, total FROM vtiger_salesorder) h
  JOIN vtiger_crmentity c ON c.crmid=h.did AND c.deleted=0 JOIN li l ON l.id=h.did)
SELECT 'rounding' k, setype, COUNT(*) docs, SUM(frac_lines>0) docs_with_fractional_line,
  SUM(frac_lines>0 AND ABS(subtotal-net_exact) < @eps) sub_eq_exact_sum,
  SUM(frac_lines>0 AND ABS(subtotal-ROUND(net_exact,2)) < @eps) sub_eq_round_of_sum,
  SUM(frac_lines>0 AND ABS(subtotal-net_line_rounded) < @eps) sub_eq_sum_of_rounded_lines,
  SUM(frac_lines>0 AND ABS(ROUND(net_exact,2)-net_line_rounded) > @eps) docs_where_methods_differ,
  SUM(frac_lines>0 AND ABS(subtotal-ROUND(subtotal,2)) > @eps) sub_with_fraction
FROM d GROUP BY setype;
SELECT 'fractional_line_shape' k, c.setype, COUNT(*) nlines, SUM(i.quantity<>ROUND(i.quantity)) frac_qty, SUM(i.listprice<>ROUND(i.listprice,2)) frac_price,
  MAX(LENGTH(SUBSTRING_INDEX(TRIM(TRAILING '0' FROM CAST(i.quantity AS CHAR)),'.',-1))) max_qty_decimals
FROM vtiger_inventoryproductrel i JOIN vtiger_crmentity c ON c.crmid=i.id AND c.deleted=0
WHERE ABS(i.quantity*i.listprice - ROUND(i.quantity*i.listprice, 2)) > 0.0000005 GROUP BY 2;
