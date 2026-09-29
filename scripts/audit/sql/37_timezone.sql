-- Q-05: hour-of-day distribution of record timestamps per era (counts only).
-- Moscow working hours 09-19 correspond to 06-16 UTC; the peak position tells the storage time zone.
SELECT 'created_hour' k,
  CASE WHEN c.createdtime < '2018-07-13' THEN '1_vtiger6_before_2018-07'
       WHEN c.createdtime < '2026-06-13' THEN '2_old_server_2018-07..2026-06'
       ELSE '3_new_server_since_2026-06-13' END era,
  HOUR(c.createdtime) h, COUNT(*) n
FROM vtiger_crmentity c
WHERE c.deleted=0 AND c.setype IN ('Invoice','SPPayments','Act','Contacts','Documents','ModComments','Accounts','Potentials','Leads','HelpDesk','ProjectTask','Documents Attachment')
  AND NOT (c.createdtime BETWEEN '2018-07-13' AND '2018-07-27') AND DATE(c.createdtime) <> '2018-11-02'
GROUP BY 2,3 ORDER BY 2,3;
SELECT 'pbx_start_hour' k, HOUR(p.starttime) h, COUNT(*) n FROM vtiger_pbxmanager p GROUP BY 2 ORDER BY 2;
SELECT 'pbx_created_vs_start' k, ROUND(TIMESTAMPDIFF(MINUTE, p.starttime, c.createdtime)/60) diff_hours, COUNT(*) n
FROM vtiger_pbxmanager p JOIN vtiger_crmentity c ON c.crmid=p.pbxmanagerid GROUP BY 2 ORDER BY 3 DESC LIMIT 6;
SELECT 'pbx_diff_by_month' k, DATE_FORMAT(p.starttime,'%Y-%m') ym, ROUND(TIMESTAMPDIFF(MINUTE, p.starttime, c.createdtime)/60) diff_hours, COUNT(*) n
FROM vtiger_pbxmanager p JOIN vtiger_crmentity c ON c.crmid=p.pbxmanagerid GROUP BY 2,3 ORDER BY 2,3;
SELECT 'modtracker_vs_modified' k, ROUND(TIMESTAMPDIFF(MINUTE, b.changedon, c.modifiedtime)/60) diff_hours, COUNT(*) n
FROM vtiger_modtracker_basic b JOIN vtiger_crmentity c ON c.crmid=b.crmid
WHERE b.id=(SELECT MAX(b2.id) FROM vtiger_modtracker_basic b2 WHERE b2.crmid=b.crmid) GROUP BY 2 ORDER BY 3 DESC LIMIT 5;
