-- Shared-table shapes: activity types, attachment owners, line-item owners (counts only).
SELECT 'activity' k, c.setype, a.activitytype, c.deleted, COUNT(*) n FROM vtiger_activity a JOIN vtiger_crmentity c ON c.crmid=a.activityid GROUP BY 2,3,4;
SELECT 'activity_without_crmentity' k, COUNT(*) n FROM vtiger_activity a LEFT JOIN vtiger_crmentity c ON c.crmid=a.activityid WHERE c.crmid IS NULL;
SELECT 'attachments' k, c.setype, c.deleted, COUNT(*) n FROM vtiger_attachments a JOIN vtiger_crmentity c ON c.crmid=a.attachmentsid GROUP BY 2,3;
SELECT 'lines' k, c.setype, c.deleted, COUNT(*) n FROM vtiger_inventoryproductrel i JOIN vtiger_crmentity c ON c.crmid=i.id GROUP BY 2,3;
SELECT 'orphan_lines' k, COUNT(*) n FROM vtiger_inventoryproductrel i LEFT JOIN vtiger_crmentity c ON c.crmid=i.id WHERE c.crmid IS NULL;
SELECT 'setype_not_in_tab' k, setype, deleted, COUNT(*) n FROM vtiger_crmentity WHERE setype NOT IN (SELECT name FROM vtiger_tab) GROUP BY 2,3;
