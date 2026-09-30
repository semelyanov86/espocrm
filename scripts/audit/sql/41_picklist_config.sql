-- Stage 03: configured picklists (all values, order, presence) of the modules that get EspoCRM enums,
-- plus sharing rules and salutation usage. Picklist values are vocabulary, not row data; still, Vtiger adds
-- imported values to picklist tables, so salutations print only standard values and long values print as length.
SELECT 'picklist' k, 'industry' pl, IF(CHAR_LENGTH(industry)>60, CONCAT('(long value ', CHAR_LENGTH(industry), ' chars)'), industry) value, IFNULL(sortorderid,0) sortorderid, presence FROM vtiger_industry
UNION ALL SELECT 'picklist', 'leadsource', IF(CHAR_LENGTH(leadsource)>60, CONCAT('(long value ', CHAR_LENGTH(leadsource), ' chars)'), leadsource), IFNULL(sortorderid,0), presence FROM vtiger_leadsource
UNION ALL SELECT 'picklist', 'leadstatus', IF(CHAR_LENGTH(leadstatus)>60, CONCAT('(long value ', CHAR_LENGTH(leadstatus), ' chars)'), leadstatus), IFNULL(sortorderid,0), presence FROM vtiger_leadstatus
UNION ALL SELECT 'picklist', 'rating', IF(CHAR_LENGTH(rating)>60, CONCAT('(long value ', CHAR_LENGTH(rating), ' chars)'), rating), IFNULL(sortorderid,0), presence FROM vtiger_rating
UNION ALL SELECT 'picklist', 'accounttype', IF(CHAR_LENGTH(accounttype)>60, CONCAT('(long value ', CHAR_LENGTH(accounttype), ' chars)'), accounttype), IFNULL(sortorderid,0), presence FROM vtiger_accounttype
UNION ALL SELECT 'picklist', 'opportunity_type', IF(CHAR_LENGTH(opportunity_type)>60, CONCAT('(long value ', CHAR_LENGTH(opportunity_type), ' chars)'), opportunity_type), IFNULL(sortorderid,0), presence FROM vtiger_opportunity_type
UNION ALL SELECT 'picklist', 'sales_stage', IF(CHAR_LENGTH(sales_stage)>60, CONCAT('(long value ', CHAR_LENGTH(sales_stage), ' chars)'), sales_stage), IFNULL(sortorderid,0), presence FROM vtiger_sales_stage
UNION ALL SELECT 'picklist', 'salutationtype', IF(salutationtype IN ('--None--','Mr.','Ms.','Mrs.','Dr.','Prof.'), salutationtype, '(non-standard value)'), IFNULL(sortorderid,0), presence FROM vtiger_salutationtype
UNION ALL SELECT 'picklist', 'cf_1107', IF(CHAR_LENGTH(cf_1107)>60, CONCAT('(long value ', CHAR_LENGTH(cf_1107), ' chars)'), cf_1107), IFNULL(sortorderid,0), presence FROM vtiger_cf_1107
UNION ALL SELECT 'picklist', 'ticketpriorities', IF(CHAR_LENGTH(ticketpriorities)>60, CONCAT('(long value ', CHAR_LENGTH(ticketpriorities), ' chars)'), ticketpriorities), IFNULL(sortorderid,0), presence FROM vtiger_ticketpriorities
UNION ALL SELECT 'picklist', 'ticketstatus', IF(CHAR_LENGTH(ticketstatus)>60, CONCAT('(long value ', CHAR_LENGTH(ticketstatus), ' chars)'), ticketstatus), IFNULL(sortorderid,0), presence FROM vtiger_ticketstatus
UNION ALL SELECT 'picklist', 'ticketseverities', IF(CHAR_LENGTH(ticketseverities)>60, CONCAT('(long value ', CHAR_LENGTH(ticketseverities), ' chars)'), ticketseverities), IFNULL(sortorderid,0), presence FROM vtiger_ticketseverities
UNION ALL SELECT 'picklist', 'ticketcategories', IF(CHAR_LENGTH(ticketcategories)>60, CONCAT('(long value ', CHAR_LENGTH(ticketcategories), ' chars)'), ticketcategories), IFNULL(sortorderid,0), presence FROM vtiger_ticketcategories
UNION ALL SELECT 'picklist', 'faqstatus', IF(CHAR_LENGTH(faqstatus)>60, CONCAT('(long value ', CHAR_LENGTH(faqstatus), ' chars)'), faqstatus), IFNULL(sortorderid,0), presence FROM vtiger_faqstatus
UNION ALL SELECT 'picklist', 'faqcategories', IF(CHAR_LENGTH(faqcategories)>60, CONCAT('(long value ', CHAR_LENGTH(faqcategories), ' chars)'), faqcategories), IFNULL(sortorderid,0), presence FROM vtiger_faqcategories
UNION ALL SELECT 'picklist', 'taskstatus', IF(CHAR_LENGTH(taskstatus)>60, CONCAT('(long value ', CHAR_LENGTH(taskstatus), ' chars)'), taskstatus), IFNULL(sortorderid,0), presence FROM vtiger_taskstatus
UNION ALL SELECT 'picklist', 'taskpriority', IF(CHAR_LENGTH(taskpriority)>60, CONCAT('(long value ', CHAR_LENGTH(taskpriority), ' chars)'), taskpriority), IFNULL(sortorderid,0), presence FROM vtiger_taskpriority
UNION ALL SELECT 'picklist', 'eventstatus', IF(CHAR_LENGTH(eventstatus)>60, CONCAT('(long value ', CHAR_LENGTH(eventstatus), ' chars)'), eventstatus), IFNULL(sortorderid,0), presence FROM vtiger_eventstatus
UNION ALL SELECT 'picklist', 'activitytype', IF(CHAR_LENGTH(activitytype)>60, CONCAT('(long value ', CHAR_LENGTH(activitytype), ' chars)'), activitytype), IFNULL(sortorderid,0), presence FROM vtiger_activitytype
UNION ALL SELECT 'picklist', 'projectstatus', IF(CHAR_LENGTH(projectstatus)>60, CONCAT('(long value ', CHAR_LENGTH(projectstatus), ' chars)'), projectstatus), IFNULL(sortorderid,0), presence FROM vtiger_projectstatus
UNION ALL SELECT 'picklist', 'projecttype', IF(CHAR_LENGTH(projecttype)>60, CONCAT('(long value ', CHAR_LENGTH(projecttype), ' chars)'), projecttype), IFNULL(sortorderid,0), presence FROM vtiger_projecttype
UNION ALL SELECT 'picklist', 'projectpriority', IF(CHAR_LENGTH(projectpriority)>60, CONCAT('(long value ', CHAR_LENGTH(projectpriority), ' chars)'), projectpriority), IFNULL(sortorderid,0), presence FROM vtiger_projectpriority
UNION ALL SELECT 'picklist', 'progress', IF(CHAR_LENGTH(progress)>60, CONCAT('(long value ', CHAR_LENGTH(progress), ' chars)'), progress), IFNULL(sortorderid,0), presence FROM vtiger_progress
UNION ALL SELECT 'picklist', 'projecttaskstatus', IF(CHAR_LENGTH(projecttaskstatus)>60, CONCAT('(long value ', CHAR_LENGTH(projecttaskstatus), ' chars)'), projecttaskstatus), IFNULL(sortorderid,0), presence FROM vtiger_projecttaskstatus
UNION ALL SELECT 'picklist', 'projecttaskpriority', IF(CHAR_LENGTH(projecttaskpriority)>60, CONCAT('(long value ', CHAR_LENGTH(projecttaskpriority), ' chars)'), projecttaskpriority), IFNULL(sortorderid,0), presence FROM vtiger_projecttaskpriority
UNION ALL SELECT 'picklist', 'projecttasktype', IF(CHAR_LENGTH(projecttasktype)>60, CONCAT('(long value ', CHAR_LENGTH(projecttasktype), ' chars)'), projecttasktype), IFNULL(sortorderid,0), presence FROM vtiger_projecttasktype
UNION ALL SELECT 'picklist', 'projecttaskprogress', IF(CHAR_LENGTH(projecttaskprogress)>60, CONCAT('(long value ', CHAR_LENGTH(projecttaskprogress), ' chars)'), projecttaskprogress), IFNULL(sortorderid,0), presence FROM vtiger_projecttaskprogress
UNION ALL SELECT 'picklist', 'usageunit', IF(CHAR_LENGTH(usageunit)>60, CONCAT('(long value ', CHAR_LENGTH(usageunit), ' chars)'), usageunit), IFNULL(sortorderid,0), presence FROM vtiger_usageunit
UNION ALL SELECT 'picklist', 'service_usageunit', IF(CHAR_LENGTH(service_usageunit)>60, CONCAT('(long value ', CHAR_LENGTH(service_usageunit), ' chars)'), service_usageunit), IFNULL(sortorderid,0), presence FROM vtiger_service_usageunit
UNION ALL SELECT 'picklist', 'servicecategory', IF(CHAR_LENGTH(servicecategory)>60, CONCAT('(long value ', CHAR_LENGTH(servicecategory), ' chars)'), servicecategory), IFNULL(sortorderid,0), presence FROM vtiger_servicecategory
ORDER BY 2, 4, 3;
-- Salutation (uitype 55 is not covered by 14_picklist_values): distribution among live records. Only standard
-- salutations are printed; anything else is counted as '(non-standard value)' so free text never leaves the host.
SELECT 'salutation_used' k, 'Leads' module,
  CASE WHEN l.salutation IS NULL OR TRIM(l.salutation)='' THEN '(empty)'
       WHEN l.salutation IN ('Mr.','Ms.','Mrs.','Dr.','Prof.') THEN l.salutation ELSE '(non-standard value)' END value,
  COUNT(*) n
FROM vtiger_leaddetails l JOIN vtiger_crmentity c ON c.crmid=l.leadid AND c.deleted=0 GROUP BY 3
UNION ALL
SELECT 'salutation_used', 'Contacts',
  CASE WHEN d.salutation IS NULL OR TRIM(d.salutation)='' THEN '(empty)'
       WHEN d.salutation IN ('Mr.','Ms.','Mrs.','Dr.','Prof.') THEN d.salutation ELSE '(non-standard value)' END,
  COUNT(*)
FROM vtiger_contactdetails d JOIN vtiger_crmentity c ON c.crmid=d.contactid AND c.deleted=0 GROUP BY 3;
-- Sharing rules: which module, from/to role and permission (0 read-only, 1 read-write).
SELECT 'share_role2role' k, r.shareid, r.share_roleid, r.to_roleid, r.permission, IFNULL(t.name,'') module, IFNULL(m.relationtype,'') relationtype
FROM vtiger_datashare_role2role r LEFT JOIN vtiger_datashare_module_rel m ON m.shareid=r.shareid LEFT JOIN vtiger_tab t ON t.tabid=m.tabid;
-- Group membership (ids only) and user→group, needed to seed EspoCRM teams.
SELECT 'users2group' k, ug.groupid, ug.userid FROM vtiger_users2group ug ORDER BY 2, 3;
-- Leads converted flag vs status (status Converted is derived from converted=1).
SELECT 'lead_converted' k, l.converted, IFNULL(NULLIF(l.leadstatus,''),'(empty)') status, COUNT(*) n
FROM vtiger_leaddetails l JOIN vtiger_crmentity c ON c.crmid=l.leadid AND c.deleted=0 GROUP BY 2, 3;
