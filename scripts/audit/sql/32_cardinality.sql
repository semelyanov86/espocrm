-- Observed cardinality of many-to-many pairs and document lines (live records only).
SELECT 'crmentityrel_card' k, r.module, r.relmodule, COUNT(*) n, MAX(a.cnt) max_per_src, MAX(b.cnt) max_per_dst
FROM vtiger_crmentityrel r
JOIN vtiger_crmentity c1 ON c1.crmid=r.crmid AND c1.deleted=0 JOIN vtiger_crmentity c2 ON c2.crmid=r.relcrmid AND c2.deleted=0
JOIN (SELECT crmid, relmodule, COUNT(*) cnt FROM vtiger_crmentityrel GROUP BY crmid, relmodule) a ON a.crmid=r.crmid AND a.relmodule=r.relmodule
JOIN (SELECT relcrmid, module, COUNT(*) cnt FROM vtiger_crmentityrel GROUP BY relcrmid, module) b ON b.relcrmid=r.relcrmid AND b.module=r.module
GROUP BY 2,3 ORDER BY 2,3;
SELECT 'doc_lines' k, c.setype, COUNT(DISTINCT i.id) docs, COUNT(*) nlines, MAX(x.cnt) max_lines
FROM vtiger_inventoryproductrel i JOIN vtiger_crmentity c ON c.crmid=i.id AND c.deleted=0
JOIN (SELECT id, COUNT(*) cnt FROM vtiger_inventoryproductrel GROUP BY id) x ON x.id=i.id GROUP BY 2;
SELECT 'doc_lines_deleted_parent' k, c.setype, COUNT(*) nlines FROM vtiger_inventoryproductrel i JOIN vtiger_crmentity c ON c.crmid=i.id AND c.deleted=1 GROUP BY 2;
SELECT 'senotes_card' k, c.setype, COUNT(*) n, MAX(x.cnt) max_docs_per_parent, MAX(y.cnt) max_parents_per_doc
FROM vtiger_senotesrel r JOIN vtiger_crmentity c ON c.crmid=r.crmid AND c.deleted=0 JOIN vtiger_crmentity d ON d.crmid=r.notesid AND d.deleted=0
JOIN (SELECT crmid, COUNT(*) cnt FROM vtiger_senotesrel GROUP BY crmid) x ON x.crmid=r.crmid
JOIN (SELECT notesid, COUNT(*) cnt FROM vtiger_senotesrel GROUP BY notesid) y ON y.notesid=r.notesid GROUP BY 2;
SELECT 'seactivity_card' k, MAX(x.cnt) max_parents_per_activity FROM (SELECT activityid, COUNT(*) cnt FROM vtiger_seactivityrel GROUP BY activityid) x;
SELECT 'payments_per_invoice' k, MAX(cnt) max_payments, SUM(cnt>1) invoices_many FROM (SELECT related_to, COUNT(*) cnt FROM sp_payments p JOIN vtiger_crmentity c ON c.crmid=p.payid AND c.deleted=0 WHERE related_to IS NOT NULL AND related_to<>0 GROUP BY related_to) t;
SELECT 'jvmes_per_chat' k, MAX(cnt) max_msgs, COUNT(*) chats FROM (SELECT relatedjivo, COUNT(*) cnt FROM vtiger_jvmes m JOIN vtiger_crmentity c ON c.crmid=m.jvmesid AND c.deleted=0 GROUP BY relatedjivo) t;
SELECT 'popup_per_call' k, MAX(cnt) max_popups FROM (SELECT callid, COUNT(*) cnt FROM vtiger_sp_callpopup GROUP BY callid) t;
SELECT 'tasks_per_project' k, MAX(cnt) max_tasks FROM (SELECT projectid, COUNT(*) cnt FROM vtiger_projecttask t JOIN vtiger_crmentity c ON c.crmid=t.projecttaskid AND c.deleted=0 GROUP BY projectid) t;
