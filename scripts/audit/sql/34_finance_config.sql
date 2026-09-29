-- Currency, taxes, charges, legal entity presence flags (no requisite values), line/header usage.
SELECT 'currency' k, id, currency_name, currency_code, currency_symbol, conversion_rate, currency_status, defaultid, deleted FROM vtiger_currency_info;
SELECT 'tax' k, taxid, taxname, taxlabel, percentage, deleted, IFNULL(method,''), IFNULL(type,''), IFNULL(compoundon,''), IFNULL(regions,'') FROM vtiger_inventorytaxinfo;
SELECT 'shtax' k, taxid, taxname, taxlabel, percentage, deleted, IFNULL(method,''), IFNULL(type,'') FROM vtiger_shippingtaxinfo;
SELECT 'charge' k, chargeid, name, format, type, value, istaxable, IFNULL(taxes,''), deleted FROM vtiger_inventorycharges;
SELECT 'spcompany_picklist' k, spcompanyid, spcompany, presence, sortorderid FROM vtiger_spcompany;
SELECT 'orgdetails' k, organization_id, IFNULL(company,'(null)') company,
  (organizationname<>'') name, (address<>'') addr, (city<>'') city, (state<>'') state, (country<>'') country, (code<>'') code, (phone<>'') phone, (fax<>'') fax,
  (website<>'') website, (logoname<>'') logoname, (logo IS NOT NULL AND logo<>'') logo, (vatid<>'') vatid, (inn<>'') inn, (kpp<>'') kpp, (bankaccount<>'') bankaccount,
  (bankname<>'') bankname, (bankid<>'') bankid, (corraccount<>'') corraccount, (director<>'') director, (bookkeeper<>'') bookkeeper, (entrepreneur<>'') entrepreneur,
  (entrepreneurreg<>'') entrepreneurreg, (okpo<>'') okpo FROM vtiger_organizationdetails;
SELECT 'line_usage' k, c.setype, SUM(i.tax1 IS NOT NULL AND i.tax1<>0) tax1_nz, SUM(i.tax2 IS NOT NULL AND i.tax2<>0) tax2_nz, SUM(i.tax3 IS NOT NULL AND i.tax3<>0) tax3_nz,
  GROUP_CONCAT(DISTINCT i.tax1) tax1_vals, SUM(i.discount_percent<>0) disc_pct_nz, SUM(i.discount_amount<>0) disc_amt_nz, SUM(i.quantity<>ROUND(i.quantity)) frac_qty,
  SUM(i.listprice<>ROUND(i.listprice,2)) price_gt2dp, SUM(i.purchase_cost<>0) pcost_nz, SUM(i.margin<>0) margin_nz, COUNT(*) n, MAX(i.sequence_no) max_seq
FROM vtiger_inventoryproductrel i JOIN vtiger_crmentity c ON c.crmid=i.id AND c.deleted=0 GROUP BY 2;
SELECT 'charges' k, c.setype, COUNT(*) n, SUM(r.charges REGEXP '"value":"?0*(\\.0+)?"?[,}]') zero_value
FROM vtiger_inventorychargesrel r JOIN vtiger_crmentity c ON c.crmid=r.recordid GROUP BY 2;
SELECT 'inv_hdr' k, taxtype, COUNT(*) n, SUM(IFNULL(discount_percent,0)<>0) dpct, SUM(IFNULL(discount_amount,0)<>0) damt, SUM(s_h_amount<>0) sh, SUM(adjustment<>0) adj,
  SUM(conversion_rate<>1) conv, SUM(received<>0) recv_nz, MIN(invoicedate), MAX(invoicedate), SUM(duedate IS NOT NULL) due
FROM vtiger_invoice i JOIN vtiger_crmentity c ON c.crmid=i.invoiceid AND c.deleted=0 GROUP BY taxtype;
-- Which formula explains subtotal, per document type (region_id NULL = documents before the 2018 upgrade).
SET @eps := 0.005;
WITH li AS (SELECT i.id, SUM(i.quantity*i.listprice - IFNULL(i.discount_amount,0) - i.quantity*i.listprice*IFNULL(i.discount_percent,0)/100) net,
  SUM((i.quantity*i.listprice - IFNULL(i.discount_amount,0))*(IFNULL(i.tax1,0)+IFNULL(i.tax2,0)+IFNULL(i.tax3,0))/100) tax FROM vtiger_inventoryproductrel i GROUP BY i.id)
SELECT 'formula_class' k, c.setype, h.taxtype,
  CASE WHEN ABS(h.subtotal-(l.net+l.tax))<@eps AND l.tax<>0 THEN 'sub=net+tax(tax>0)' WHEN ABS(h.subtotal-l.net)<@eps AND l.tax=0 THEN 'sub=net(no tax)'
       WHEN ABS(h.subtotal-l.net)<@eps AND l.tax<>0 THEN 'sub=net(tax on lines ignored)' ELSE 'other' END cls,
  COUNT(*) n, MIN(YEAR(c.createdtime)) y_min, MAX(YEAR(c.createdtime)) y_max, IFNULL(GROUP_CONCAT(DISTINCT h.region_id),'null') regions
FROM (SELECT invoiceid id, taxtype, subtotal, region_id FROM vtiger_invoice UNION ALL SELECT quoteid, taxtype, subtotal, region_id FROM vtiger_quotes
      UNION ALL SELECT salesorderid, taxtype, subtotal, region_id FROM vtiger_salesorder UNION ALL SELECT actid, taxtype, subtotal, region_id FROM vtiger_sp_act) h
JOIN vtiger_crmentity c ON c.crmid=h.id AND c.deleted=0 JOIN li l ON l.id=h.id GROUP BY 2,3,4 ORDER BY 2,3,4;
SELECT 'balance_ne_total' k, invoicestatus, SUM(balance=0) bal_zero, COUNT(*) n FROM vtiger_invoice h JOIN vtiger_crmentity c ON c.crmid=h.invoiceid AND c.deleted=0 WHERE ABS(balance-total)>=@eps GROUP BY 2;
SELECT 'pay_year' k, YEAR(c.createdtime) y, COUNT(*) n, SUM(cf.cf_1204 IS NOT NULL AND cf.cf_1204<>'') bank_txid, SUM(p.doc_no IS NOT NULL AND p.doc_no<>0) doc_no,
  SUM(p.related_to IS NOT NULL AND p.related_to<>0) linked_inv, SUM(p.spcompany IS NULL OR p.spcompany='') no_company
FROM sp_payments p JOIN sp_paymentscf cf ON cf.payid=p.payid JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0 GROUP BY 2 ORDER BY 2;
SELECT 'account_inn' k, COUNT(*) n, SUM(a.inn IS NOT NULL AND a.inn<>'') inn_nz, SUM(a.kpp IS NOT NULL AND a.kpp<>'') kpp_nz FROM vtiger_account a JOIN vtiger_crmentity c ON c.crmid=a.accountid AND c.deleted=0;
SELECT 'invoice_year' k, YEAR(invoicedate) y, COUNT(*) n, SUM(invoicestatus='Paid') paid, SUM(spcompany='Default') def_en, SUM(spcompany='По умолчанию') def_ru, SUM(taxtype='group_tax_inc') tax_inc
FROM vtiger_invoice i JOIN vtiger_crmentity c ON c.crmid=i.invoiceid AND c.deleted=0 GROUP BY 2 ORDER BY 2;
