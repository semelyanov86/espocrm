-- Module activity timeline (dates only).
SELECT 'timeline' kind, setype, deleted, MIN(createdtime) first_created, MAX(createdtime) last_created, MAX(modifiedtime) last_modified, COUNT(*) n
FROM vtiger_crmentity GROUP BY setype, deleted ORDER BY setype, deleted;
SELECT 'created_per_year' kind, setype, YEAR(createdtime) y, COUNT(*) n FROM vtiger_crmentity WHERE deleted=0 GROUP BY 2,3 ORDER BY 2,3;
-- Workflows: metadata and condition field names only.
SELECT 'workflow' kind, w.workflow_id, w.module_name, REPLACE(REPLACE(w.summary,'\t',' '),'\n',' ') summary, IFNULL(w.workflowname,'') workflowname,
  w.execution_condition, CASE w.execution_condition WHEN 1 THEN 'ON_FIRST_SAVE' WHEN 2 THEN 'ONCE' WHEN 3 THEN 'ON_EVERY_SAVE' WHEN 4 THEN 'ON_MODIFY' WHEN 5 THEN 'ON_DELETE' WHEN 6 THEN 'ON_SCHEDULE' WHEN 7 THEN 'MANUAL' ELSE 'other' END cond_name,
  w.defaultworkflow, IFNULL(w.type,'') type, w.status, IFNULL(w.schtypeid,'') schtypeid, IFNULL(w.nexttrigger_time,'') nexttrigger,
  IFNULL(JSON_UNQUOTE(JSON_EXTRACT(IF(JSON_VALID(w.test), w.test, '[]'), '$[*].fieldname')),'') condition_fields
FROM com_vtiger_workflows w ORDER BY w.module_name, w.workflow_id;
SELECT 'workflowtask' kind, t.task_id, t.workflow_id, w.module_name, REPLACE(REPLACE(t.summary,'\t',' '),'\n',' ') summary,
  SUBSTRING_INDEX(SUBSTRING_INDEX(t.task,'"',2),'"',-1) task_class,
  IFNULL(REGEXP_SUBSTR(t.task, 's:6:"active";(b:[01]|s:[0-9]+:"[^"]*"|i:[0-9]+)'),'') active_flag,
  IFNULL(REGEXP_SUBSTR(t.task, 's:10:"methodName";s:[0-9]+:"[^"]+"'),'') method,
  IFNULL(REGEXP_SUBSTR(t.task, '\\\\?"fieldname\\\\?":\\\\?"[A-Za-z0-9_]+', 1, 1),'') f1,
  IFNULL(REGEXP_SUBSTR(t.task, '\\\\?"fieldname\\\\?":\\\\?"[A-Za-z0-9_]+', 1, 2),'') f2,
  IFNULL(REGEXP_SUBSTR(t.task, '\\\\?"fieldname\\\\?":\\\\?"[A-Za-z0-9_]+', 1, 3),'') f3,
  IFNULL(REGEXP_SUBSTR(t.task, '\\\\?"fieldname\\\\?":\\\\?"[A-Za-z0-9_]+', 1, 4),'') f4,
  IFNULL(REGEXP_SUBSTR(t.task, 's:12:"entity_type";s:[0-9]+:"[^"]+"'),'') entity_type
FROM com_vtiger_workflowtasks t LEFT JOIN com_vtiger_workflows w ON w.workflow_id=t.workflow_id ORDER BY t.workflow_id, t.task_id;
SELECT 'entitymethod' kind, workflowtasks_entitymethod_id, module_name, method_name, function_path, function_name FROM com_vtiger_workflowtasks_entitymethod;
SELECT 'tasktype' kind, id, tasktypename, label, classname, IFNULL(modules,'') modules FROM com_vtiger_workflow_tasktypes;
-- Scheduler, handlers, links.
SELECT 'cron' kind, id, name, handler_file, frequency, status, IFNULL(FROM_UNIXTIME(laststart),'') laststart, IFNULL(FROM_UNIXTIME(lastend),'') lastend, IFNULL(module,'') module FROM vtiger_cron_task ORDER BY sequence;
SELECT 'eventhandler' kind, eventhandler_id, event_name, handler_path, handler_class, is_active, IFNULL(cond,'') cond FROM vtiger_eventhandlers ORDER BY eventhandler_id;
SELECT 'link' kind, l.linkid, IFNULL(t.name,'(global)') module, l.linktype, l.linklabel, IFNULL(l.handler_class,'') handler_class FROM vtiger_links l LEFT JOIN vtiger_tab t ON t.tabid=l.tabid
WHERE l.linktype NOT IN ('HEADERSCRIPT','HEADERCSS') OR l.linkurl NOT LIKE 'layouts/%' ORDER BY 3,4;
SELECT 'headerscript' kind, COUNT(*) n, GROUP_CONCAT(DISTINCT SUBSTRING_INDEX(SUBSTRING_INDEX(linkurl,'/',-2),'/',1)) dirs FROM vtiger_links WHERE linktype IN ('HEADERSCRIPT','HEADERCSS');
-- Reports / filters (definitions only).
SELECT 'report' kind, r.reportid, r.reportname, r.reporttype, IFNULL(m.primarymodule,'') primarymodule, IFNULL(m.secondarymodules,'') secondary, IFNULL(r.sharingtype,'') sharing, r.owner FROM vtiger_report r LEFT JOIN vtiger_reportmodules m ON m.reportmodulesid=r.reportid ORDER BY r.reportid;
SELECT 'customview' kind, entitytype, COUNT(*) n, SUM(setdefault=1) defaults, SUM(status=0) default_status0, SUM(userid<>1) other_users FROM vtiger_customview GROUP BY entitytype ORDER BY entitytype;
-- Change history.
SELECT 'modtracker' kind, b.module, b.status, CASE b.status WHEN 0 THEN 'UPDATED' WHEN 1 THEN 'DELETED' WHEN 2 THEN 'CREATED' WHEN 3 THEN 'RESTORED' WHEN 4 THEN 'LINK' WHEN 5 THEN 'UNLINK' ELSE 'other' END st,
  MIN(b.changedon) first, MAX(b.changedon) last, COUNT(*) n FROM vtiger_modtracker_basic b GROUP BY 2,3 ORDER BY 2,3;
SELECT 'modtracker_detail' kind, b.module, COUNT(*) n, COUNT(DISTINCT d.fieldname) fields FROM vtiger_modtracker_detail d JOIN vtiger_modtracker_basic b ON b.id=d.id GROUP BY 2 ORDER BY 2;
SELECT 'modtracker_sensitive' kind, b.module, d.fieldname, COUNT(*) n, SUM(d.prevalue IS NOT NULL AND d.prevalue<>'') prev_nonempty, SUM(d.postvalue IS NOT NULL AND d.postvalue<>'') post_nonempty
FROM vtiger_modtracker_detail d JOIN vtiger_modtracker_basic b ON b.id=d.id WHERE d.fieldname IN ('cf_1322','cf_1324','cf_1326','cf_1328') GROUP BY 2,3;
SELECT 'modtracker_relations' kind, b.module, r.targetmodule, COUNT(*) n FROM vtiger_modtracker_relations r JOIN vtiger_modtracker_basic b ON b.id=r.id GROUP BY 2,3 ORDER BY 2,3;
SELECT 'modtracker_tabs' kind, t.name, mt.visible FROM vtiger_modtracker_tabs mt JOIN vtiger_tab t ON t.tabid=mt.tabid WHERE mt.visible=1 ORDER BY 2;
SELECT 'statushistory' kind, 'invoice' t, COUNT(*) n, MIN(lastmodified), MAX(lastmodified) FROM vtiger_invoicestatushistory
UNION ALL SELECT 'statushistory','act', COUNT(*), MIN(lastmodified), MAX(lastmodified) FROM vtiger_sp_actstatushistory
UNION ALL SELECT 'statushistory','potstage', COUNT(*), MIN(lastmodified), MAX(lastmodified) FROM vtiger_potstagehistory;
SELECT 'tags' kind, f.module, COUNT(*) n, COUNT(DISTINCT f.tag_id) distinct_tags FROM vtiger_freetagged_objects f GROUP BY 2;
