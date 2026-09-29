SELECT 'doc_folders' k, f.folderid, f.foldername, COUNT(n.notesid) n FROM vtiger_attachmentsfolder f LEFT JOIN vtiger_notes n ON n.folderid=f.folderid GROUP BY 2,3;
SELECT 'doc_shape' k, n.filelocationtype, SUM(n.filename IS NULL OR n.filename='') no_filename,
  SUM(n.filelocationtype='I' AND NOT EXISTS(SELECT 1 FROM vtiger_seattachmentsrel r WHERE r.crmid=n.notesid)) internal_without_attachment,
  SUM(n.filelocationtype='E' AND n.filename LIKE 'http%') external_http, SUM(n.notecontent IS NOT NULL AND n.notecontent<>'') with_note, SUM(n.filesize) bytes, COUNT(*) n,
  SUM(EXISTS(SELECT 1 FROM vtiger_senotesrel s WHERE s.notesid=n.notesid)) linked_to_record
FROM vtiger_notes n JOIN vtiger_crmentity c ON c.crmid=n.notesid AND c.deleted=0 GROUP BY 2;
SELECT 'doc_mime' k, SUBSTRING_INDEX(a.type,'/',1) major, COUNT(*) n FROM vtiger_attachments a JOIN vtiger_crmentity c ON c.crmid=a.attachmentsid AND c.deleted=0 AND c.setype='Documents Attachment' GROUP BY 2;
SELECT 'mail_accounts' k, COUNT(*) n, SUM(status='1' OR status='active') active, GROUP_CONCAT(DISTINCT mail_protocol) protocols FROM vtiger_mail_accounts;
SELECT 'mailscanner' k, (SELECT COUNT(*) FROM vtiger_mailscanner) scanners, (SELECT COUNT(*) FROM vtiger_mailscanner_rules) rules, (SELECT COUNT(*) FROM vtiger_mailscanner_ids) seen_ids;
SELECT 'mailmanager' k, (SELECT COUNT(*) FROM vtiger_mailmanager_mailrecord) records, (SELECT COUNT(*) FROM vtiger_mailmanager_mailattachments) atts, (SELECT COUNT(*) FROM vtiger_mailmanager_mailrel) rels;
SELECT 'emails_shape' k, SUM(e.from_email<>'') from_nz, SUM(e.to_email<>'') to_nz, SUM(e.cc_email IS NOT NULL AND e.cc_email NOT IN ('','[]')) cc_nz, SUM(c.description IS NOT NULL AND c.description<>'') body_nz, COUNT(*) n
FROM vtiger_emaildetails e JOIN vtiger_activity a ON a.activityid=e.emailid JOIN vtiger_crmentity c ON c.crmid=e.emailid AND c.deleted=0;
SELECT 'google' k, (SELECT COUNT(*) FROM vtiger_google_oauth2) oauth_rows, (SELECT COUNT(*) FROM vtiger_google_sync) sync_rows, (SELECT COUNT(*) FROM vtiger_google_event_calendar_mapping) event_map, (SELECT COUNT(*) FROM vtiger_wsapp_recordmapping) wsapp_map;
SELECT 'portal' k, (SELECT COUNT(*) FROM vtiger_portalinfo) portal_users, (SELECT SUM(isactive) FROM vtiger_portalinfo) active_portal_users, (SELECT COUNT(*) FROM vtiger_customerportal_tabs WHERE visible=1) visible_tabs;
SELECT 'webforms' k, COUNT(*) n FROM vtiger_webforms;
SELECT 'convertlead' k, COUNT(*) n, SUM(accountfid<>0) to_acc, SUM(contactfid<>0) to_cont, SUM(potentialfid<>0) to_pot FROM vtiger_convertleadmapping;
SELECT 'reminders' k, (SELECT COUNT(*) FROM vtiger_activity_reminder) reminders, (SELECT SUM(reminder_sent) FROM vtiger_activity_reminder) sent, (SELECT COUNT(*) FROM vtiger_activity_reminder_popup) popups;
SELECT 'masked_inputs' k, COUNT(*) n FROM masked_inputs;
SELECT 'vte_conditional_alerts' k, COUNT(*) n FROM vte_conditional_alerts;
SELECT 'globalsearch' k, COUNT(*) n FROM berli_globalsearch_data;
SELECT 'user_prefs' k, (SELECT COUNT(*) FROM vtiger_user_module_preferences) module_prefs, (SELECT COUNT(*) FROM vtiger_module_dashboard_widgets) widgets;
