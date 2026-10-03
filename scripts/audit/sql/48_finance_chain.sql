-- Stage 04.6: the end-to-end finance chain of the source (aggregates only, no row values).
-- Which chains exist (quote → order → invoice → act, payments), and whether linked documents agree on account,
-- contact, owner, legal entity and tax regime — the fields a conversion copies in EspoCRM.

-- 1. Chain shape of every live invoice: sales order, act, payments (related_to or the related list).
WITH inv AS (
  SELECT i.invoiceid id, i.invoicestatus st,
         (so.salesorderid IS NOT NULL) has_so, (so.quoteid IS NOT NULL AND so.quoteid <> 0) so_has_quote,
         (a.actid IS NOT NULL) has_act,
         EXISTS (SELECT 1 FROM sp_payments p JOIN vtiger_crmentity pc ON pc.crmid=p.payid AND pc.deleted=0
                 WHERE p.related_to=i.invoiceid
                    OR EXISTS (SELECT 1 FROM vtiger_crmentityrel r WHERE r.relmodule='SPPayments' AND r.relcrmid=p.payid
                               AND r.crmid=i.invoiceid)) has_pay
  FROM vtiger_invoice i JOIN vtiger_crmentity c ON c.crmid=i.invoiceid AND c.deleted=0
  LEFT JOIN vtiger_salesorder so ON so.salesorderid=i.salesorderid
       AND EXISTS (SELECT 1 FROM vtiger_crmentity sc WHERE sc.crmid=so.salesorderid AND sc.deleted=0)
  LEFT JOIN vtiger_sp_act a ON a.actid=i.sp_act_id
       AND EXISTS (SELECT 1 FROM vtiger_crmentity ac WHERE ac.crmid=a.actid AND ac.deleted=0))
SELECT 'chain_shape' k, has_so, so_has_quote, has_act, has_pay, COUNT(*) n FROM inv GROUP BY 2,3,4,5 ORDER BY 2,3,4,5;

-- 2. Quotes and sales orders outside invoices.
SELECT 'quote_links' k, COUNT(*) quotes,
  SUM(EXISTS (SELECT 1 FROM vtiger_salesorder s JOIN vtiger_crmentity sc ON sc.crmid=s.salesorderid AND sc.deleted=0 WHERE s.quoteid=q.quoteid)) with_order
FROM vtiger_quotes q JOIN vtiger_crmentity c ON c.crmid=q.quoteid AND c.deleted=0;
SELECT 'order_links' k, COUNT(*) orders,
  SUM(EXISTS (SELECT 1 FROM vtiger_invoice i JOIN vtiger_crmentity ic ON ic.crmid=i.invoiceid AND ic.deleted=0 WHERE i.salesorderid=s.salesorderid)) with_invoice,
  SUM(EXISTS (SELECT 1 FROM sp_payments p JOIN vtiger_crmentity pc ON pc.crmid=p.payid AND pc.deleted=0 WHERE p.related_to=s.salesorderid)) with_payment,
  SUM(EXISTS (SELECT 1 FROM vtiger_invoice i JOIN vtiger_crmentity ic ON ic.crmid=i.invoiceid AND ic.deleted=0 WHERE i.salesorderid=s.salesorderid)
      AND EXISTS (SELECT 1 FROM sp_payments p JOIN vtiger_crmentity pc ON pc.crmid=p.payid AND pc.deleted=0 WHERE p.related_to=s.salesorderid)) invoice_and_payment
FROM vtiger_salesorder s JOIN vtiger_crmentity c ON c.crmid=s.salesorderid AND c.deleted=0;
-- Orders paid directly and invoiced: are their invoices paid too (settled independently in EspoCRM, Q-43)?
SELECT 'order_paid_and_invoiced' k, COUNT(DISTINCT s.salesorderid) orders,
  COUNT(DISTINCT CASE WHEN EXISTS (SELECT 1 FROM sp_payments p JOIN vtiger_crmentity pc ON pc.crmid=p.payid AND pc.deleted=0
      WHERE p.related_to=i.invoiceid OR EXISTS (SELECT 1 FROM vtiger_crmentityrel r WHERE r.relmodule='SPPayments'
                                                AND r.relcrmid=p.payid AND r.crmid=i.invoiceid))
      THEN s.salesorderid END) orders_with_paid_invoice,
  COUNT(DISTINCT i.invoiceid) invoices
FROM vtiger_salesorder s JOIN vtiger_crmentity sc ON sc.crmid=s.salesorderid AND sc.deleted=0
JOIN vtiger_invoice i ON i.salesorderid=s.salesorderid JOIN vtiger_crmentity ic ON ic.crmid=i.invoiceid AND ic.deleted=0
WHERE EXISTS (SELECT 1 FROM sp_payments p JOIN vtiger_crmentity pc ON pc.crmid=p.payid AND pc.deleted=0
              WHERE p.related_to=s.salesorderid);

-- 3. Linked pairs: do they agree on the fields a conversion copies?
WITH pairs AS (
  SELECT 'SalesOrder→Invoice' pair, s.accountid a1, i.accountid a2, s.contactid c1, i.contactid c2, sc.smownerid o1, ic.smownerid o2,
         s.spcompany e1, i.spcompany e2, s.taxtype t1, i.taxtype t2, s.total g1, i.total g2, sc.createdtime d1, ic.createdtime d2
  FROM vtiger_invoice i JOIN vtiger_crmentity ic ON ic.crmid=i.invoiceid AND ic.deleted=0
  JOIN vtiger_salesorder s ON s.salesorderid=i.salesorderid JOIN vtiger_crmentity sc ON sc.crmid=s.salesorderid AND sc.deleted=0
  UNION ALL
  SELECT 'Invoice→Act', i.accountid, a.accountid, i.contactid, a.contactid, ic.smownerid, ac.smownerid,
         i.spcompany, a.spcompany, i.taxtype, a.taxtype, i.total, a.total, ic.createdtime, ac.createdtime
  FROM vtiger_invoice i JOIN vtiger_crmentity ic ON ic.crmid=i.invoiceid AND ic.deleted=0
  JOIN vtiger_sp_act a ON a.actid=i.sp_act_id JOIN vtiger_crmentity ac ON ac.crmid=a.actid AND ac.deleted=0)
SELECT 'pair_agreement' k, pair, COUNT(*) n,
  SUM(a1 <=> a2) same_account, SUM(IFNULL(c1,0) = IFNULL(c2,0)) same_contact, SUM(o1 <=> o2) same_owner,
  SUM(IF(e1 IN ('', 'По умолчанию') OR e1 IS NULL, 'Default', e1) = IF(e2 IN ('', 'По умолчанию') OR e2 IS NULL, 'Default', e2)) same_legal_entity,
  SUM(t1 <=> t2) same_tax_regime, SUM(g1 = g2) same_total, SUM(d2 >= d1) target_created_later
FROM pairs GROUP BY 2 ORDER BY 2;

-- 4. Payments and their documents: payer and owner (allocation as in D-11: related_to, else the related list).
WITH alloc AS (
  SELECT p.payid, p.pay_type, p.payer, pc.smownerid po, COALESCE(NULLIF(p.related_to, 0),
         (SELECT MIN(r.crmid) FROM vtiger_crmentityrel r WHERE r.relmodule='SPPayments' AND r.relcrmid=p.payid
                 AND r.module IN ('Invoice','SalesOrder'))) doc
  FROM sp_payments p JOIN vtiger_crmentity pc ON pc.crmid=p.payid AND pc.deleted=0),
docs AS (
  SELECT i.invoiceid id, 'Invoice' m, i.accountid acc, c.smownerid o FROM vtiger_invoice i JOIN vtiger_crmentity c ON c.crmid=i.invoiceid AND c.deleted=0
  UNION ALL SELECT s.salesorderid, 'SalesOrder', s.accountid, c.smownerid FROM vtiger_salesorder s JOIN vtiger_crmentity c ON c.crmid=s.salesorderid AND c.deleted=0)
SELECT 'payment_agreement' k, d.m, a.pay_type, COUNT(*) n, SUM(a.payer <=> d.acc) payer_is_account, SUM(a.po <=> d.o) same_owner
FROM alloc a JOIN docs d ON d.id=a.doc GROUP BY 2,3 ORDER BY 2,3;

-- 5. Status of invoices along the chain (the status is set by hand: D-26).
WITH inv AS (
  SELECT IF(i.invoicestatus IS NULL OR i.invoicestatus='', '(empty)', i.invoicestatus) st,
         (i.sp_act_id IS NOT NULL AND EXISTS (SELECT 1 FROM vtiger_crmentity ac WHERE ac.crmid=i.sp_act_id AND ac.deleted=0)) has_act
  FROM vtiger_invoice i JOIN vtiger_crmentity c ON c.crmid=i.invoiceid AND c.deleted=0)
SELECT 'invoice_status_act' k, st, has_act, COUNT(*) n FROM inv GROUP BY 2,3 ORDER BY 2,3;

-- 6. Owners and creators of finance records (how many distinct users; is the owner the creator).
SELECT 'owners' k, c.setype, COUNT(DISTINCT c.smownerid) owners, COUNT(DISTINCT c.smcreatorid) creators,
  SUM(c.smownerid <> c.smcreatorid) owner_is_not_creator, COUNT(*) n
FROM vtiger_crmentity c WHERE c.deleted=0 AND c.setype IN ('Quotes','SalesOrder','Invoice','Act','SPPayments') GROUP BY 2 ORDER BY 2;
