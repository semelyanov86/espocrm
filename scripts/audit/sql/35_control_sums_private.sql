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
