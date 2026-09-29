-- Related-list definitions (metadata only).
SELECT 'relatedlist' kind, t1.name module, IFNULL(t2.name,'') related_module, r.name fn, r.label, IFNULL(r.relationtype,'') relationtype,
  IFNULL(f.fieldname,'') relationfield, r.presence, IFNULL(r.actions,'') actions
FROM vtiger_relatedlists r JOIN vtiger_tab t1 ON t1.tabid=r.tabid LEFT JOIN vtiger_tab t2 ON t2.tabid=r.related_tabid
LEFT JOIN vtiger_field f ON f.fieldid=r.relationfieldid ORDER BY t1.name, r.sequence;
-- uitype 10 allowed targets.
SELECT 'fieldmodulerel' kind, t.name module, f.fieldname, fm.relmodule, fm.status, IFNULL(fm.sequence,'') seq
FROM vtiger_fieldmodulerel fm JOIN vtiger_field f ON f.fieldid=fm.fieldid JOIN vtiger_tab t ON t.tabid=f.tabid ORDER BY 2,3,4;
-- Generic many-to-many.
SELECT 'crmentityrel' kind, r.module, IFNULL(c1.setype,'(missing)') src_setype, IFNULL(c1.deleted,'') src_del,
  r.relmodule, IFNULL(c2.setype,'(missing)') dst_setype, IFNULL(c2.deleted,'') dst_del, COUNT(*) n
FROM vtiger_crmentityrel r LEFT JOIN vtiger_crmentity c1 ON c1.crmid=r.crmid LEFT JOIN vtiger_crmentity c2 ON c2.crmid=r.relcrmid
GROUP BY 2,3,4,5,6,7 ORDER BY 2,5;
SELECT 'seactivityrel' kind, IFNULL(c.setype,'(missing)') parent_setype, IFNULL(c.deleted,'') parent_del, a.activitytype, IFNULL(ca.deleted,'') act_del, COUNT(*) n
FROM vtiger_seactivityrel r LEFT JOIN vtiger_crmentity c ON c.crmid=r.crmid LEFT JOIN vtiger_activity a ON a.activityid=r.activityid
LEFT JOIN vtiger_crmentity ca ON ca.crmid=r.activityid GROUP BY 2,3,4,5;
SELECT 'cntactivityrel' kind, a.activitytype, IFNULL(ca.deleted,'') act_del, IFNULL(c.deleted,'') contact_del, COUNT(*) n
FROM vtiger_cntactivityrel r LEFT JOIN vtiger_activity a ON a.activityid=r.activityid LEFT JOIN vtiger_crmentity ca ON ca.crmid=r.activityid
LEFT JOIN vtiger_crmentity c ON c.crmid=r.contactid GROUP BY 2,3,4;
SELECT 'salesmanactivityrel' kind, a.activitytype, IFNULL(ca.deleted,'') act_del, COUNT(*) n FROM vtiger_salesmanactivityrel r
LEFT JOIN vtiger_activity a ON a.activityid=r.activityid LEFT JOIN vtiger_crmentity ca ON ca.crmid=r.activityid GROUP BY 2,3;
SELECT 'invitees' kind, a.activitytype, IFNULL(ca.deleted,'') act_del, COUNT(*) n FROM vtiger_invitees r
LEFT JOIN vtiger_activity a ON a.activityid=r.activityid LEFT JOIN vtiger_crmentity ca ON ca.crmid=r.activityid GROUP BY 2,3;
SELECT 'senotesrel' kind, IFNULL(c.setype,'(missing)') parent_setype, IFNULL(c.deleted,'') parent_del, IFNULL(cn.deleted,'') note_del, COUNT(*) n
FROM vtiger_senotesrel r LEFT JOIN vtiger_crmentity c ON c.crmid=r.crmid LEFT JOIN vtiger_crmentity cn ON cn.crmid=r.notesid GROUP BY 2,3,4;
SELECT 'seattachmentsrel' kind, IFNULL(c.setype,'(missing)') parent_setype, IFNULL(c.deleted,'') parent_del, IFNULL(ca.setype,'(missing)') att_setype, IFNULL(ca.deleted,'') att_del, COUNT(*) n
FROM vtiger_seattachmentsrel r LEFT JOIN vtiger_crmentity c ON c.crmid=r.crmid LEFT JOIN vtiger_crmentity ca ON ca.crmid=r.attachmentsid GROUP BY 2,3,4,5;
SELECT 'contpotentialrel' kind, IFNULL(c1.deleted,'') contact_del, IFNULL(c2.deleted,'') pot_del, COUNT(*) n FROM vtiger_contpotentialrel r
LEFT JOIN vtiger_crmentity c1 ON c1.crmid=r.contactid LEFT JOIN vtiger_crmentity c2 ON c2.crmid=r.potentialid GROUP BY 2,3;
SELECT 'seproductsrel' kind, r.setype, IFNULL(c.deleted,'') del, COUNT(*) n FROM vtiger_seproductsrel r LEFT JOIN vtiger_crmentity c ON c.crmid=r.crmid GROUP BY 2,3;
SELECT 'vendorcontactrel' kind, COUNT(*) n FROM vtiger_vendorcontactrel;
SELECT 'campaignrels' kind, (SELECT COUNT(*) FROM vtiger_campaigncontrel) contrel, (SELECT COUNT(*) FROM vtiger_campaignleadrel) leadrel, (SELECT COUNT(*) FROM vtiger_campaignaccountrel) accrel;
SELECT 'crmentity_user_field' kind, c.setype, SUM(u.starred='1') starred, COUNT(*) n FROM vtiger_crmentity_user_field u JOIN vtiger_crmentity c ON c.crmid=u.recordid GROUP BY 2;
SELECT 'modcomments_userid' kind, SUM(u.id IS NOT NULL) matches_user, SUM(u.id IS NULL AND m.userid IS NOT NULL AND m.userid<>0) nonuser, COUNT(*) n
FROM vtiger_modcomments m LEFT JOIN vtiger_users u ON u.id=m.userid;
