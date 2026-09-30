-- Stage 03: facts the EspoCRM model depends on (counts and extremes only, no row values).
-- Project.targetbudget is varchar in Vtiger: how many values are plain numbers (→ currency field).
SELECT 'project_budget' k, COUNT(*) live, SUM(p.targetbudget IS NOT NULL AND TRIM(p.targetbudget)<>'') nonempty,
  SUM(TRIM(p.targetbudget) REGEXP '^[0-9]+([.,][0-9]{1,2})?$') numeric_plain
FROM vtiger_project p JOIN vtiger_crmentity c ON c.crmid=p.projectid AND c.deleted=0;
-- Numeric ranges of int/decimal targets.
SELECT 'pt_hours' k, MIN(projecttaskhours) mn, MAX(projecttaskhours) mx, SUM(projecttaskhours<0) neg
FROM vtiger_projecttask t JOIN vtiger_crmentity c ON c.crmid=t.projecttaskid AND c.deleted=0;
SELECT 'svc_qty' k, MIN(NULLIF(qty_per_unit,0)) mn, MAX(qty_per_unit) mx FROM vtiger_service s JOIN vtiger_crmentity c ON c.crmid=s.serviceid AND c.deleted=0;
SELECT 'acc_employees' k, MAX(employees) mx FROM vtiger_account a JOIN vtiger_crmentity c ON c.crmid=a.accountid AND c.deleted=0;
-- Activities without dates by type (EspoCRM requires dates for Call/Meeting).
SELECT 'event_dates' k, a.activitytype, COUNT(*) n,
  SUM(a.date_start IS NULL OR CAST(a.date_start AS CHAR) LIKE '0000%') no_start,
  SUM(a.due_date IS NULL OR CAST(a.due_date AS CHAR) LIKE '0000%') no_end
FROM vtiger_activity a JOIN vtiger_crmentity c ON c.crmid=a.activityid AND c.deleted=0 AND c.setype='Calendar'
GROUP BY 2;
SELECT 'pbx_no_end' k, COUNT(*) n, SUM(totalduration IS NULL OR totalduration=0) zero_duration
FROM vtiger_pbxmanager p JOIN vtiger_crmentity c ON c.crmid=p.pbxmanagerid AND c.deleted=0
WHERE p.endtime IS NULL OR CAST(p.endtime AS CHAR) LIKE '0000%';
-- Opportunities without amount (EspoCRM core makes amount required).
SELECT 'potential_no_amount' k, SUM(p.amount IS NULL OR p.amount=0) n FROM vtiger_potential p JOIN vtiger_crmentity c ON c.crmid=p.potentialid AND c.deleted=0;
-- Export/import/merge utilities of the profiles of the used roles (module names only).
SELECT 'utility' k, p.profilename, a.actionname, SUM(u.permission=0) allowed_modules, SUM(u.permission<>0) denied_modules
FROM vtiger_profile2utility u JOIN vtiger_profile p ON p.profileid=u.profileid
JOIN vtiger_actionmapping a ON a.actionid=u.activityid AND a.securitycheck=0
JOIN vtiger_tab t ON t.tabid=u.tabid AND t.presence IN (0,2)
WHERE p.profileid IN (1,5,6,10) AND a.actionname IN ('Export','Import','Merge')
GROUP BY 2,3 ORDER BY 2,3;
-- Assignment scope of roles (allowassignedrecordsto: 1 = all users).
SELECT 'role_assign' k, roleid, rolename, allowassignedrecordsto FROM vtiger_role ORDER BY parentrole;
