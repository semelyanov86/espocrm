-- Users without names/emails: id, status, admin flag, role.
SELECT 'user' kind, u.id, u.status, u.is_admin, IFNULL(r.rolename,'') role, IFNULL(u2r.roleid,'') roleid, u.deleted,
  (u.user_name IS NOT NULL AND u.user_name<>'') has_login, IFNULL(u.currency_id,'') currency_id, IFNULL(u.language,'') language, IFNULL(u.time_zone,'') tz,
  (SELECT COUNT(*) FROM vtiger_asteriskextensions e WHERE e.userid=u.id AND e.asterisk_extension IS NOT NULL AND e.asterisk_extension<>'') has_extension,
  IFNULL(u.phone_crm_extension IS NOT NULL AND u.phone_crm_extension<>'', '') has_crm_ext
FROM vtiger_users u LEFT JOIN vtiger_user2role u2r ON u2r.userid=u.id LEFT JOIN vtiger_role r ON r.roleid=u2r.roleid ORDER BY u.id;
SELECT 'role' kind, roleid, rolename, parentrole, depth, IFNULL(allowassignedrecordsto,'') allowassign FROM vtiger_role ORDER BY parentrole;
SELECT 'profile' kind, p.profileid, p.profilename, p.directly_related_to_role, GROUP_CONCAT(r2p.roleid) roles FROM vtiger_profile p LEFT JOIN vtiger_role2profile r2p ON r2p.profileid=p.profileid GROUP BY p.profileid;
SELECT 'group' kind, g.groupid, g.groupname, (SELECT COUNT(*) FROM vtiger_users2group ug WHERE ug.groupid=g.groupid) users,
  (SELECT COUNT(*) FROM vtiger_group2role gr WHERE gr.groupid=g.groupid) roles, (SELECT COUNT(*) FROM vtiger_group2rs grs WHERE grs.groupid=g.groupid) rs,
  (SELECT COUNT(*) FROM vtiger_group2grouprel gg WHERE gg.groupid=g.groupid) subgroups FROM vtiger_groups g;
SELECT 'def_org_share' kind, t.name module, d.permission, CASE d.permission WHEN 0 THEN 'Public: Read Only' WHEN 1 THEN 'Public: Read, Create/Edit' WHEN 2 THEN 'Public: Read, Create/Edit, Delete' WHEN 3 THEN 'Private' ELSE 'other' END meaning, d.editstatus
FROM vtiger_def_org_share d JOIN vtiger_tab t ON t.tabid=d.tabid ORDER BY t.name;
SELECT 'profile2tab_hidden' kind, p.profilename, t.name module, pt.permissions FROM vtiger_profile2tab pt JOIN vtiger_profile p ON p.profileid=pt.profileid JOIN vtiger_tab t ON t.tabid=pt.tabid
WHERE pt.permissions<>0 AND t.presence IN (0,2) ORDER BY 2,3;
SELECT 'profile2standard_denied' kind, p.profilename, t.name module, ps.operation, ps.permissions FROM vtiger_profile2standardpermissions ps JOIN vtiger_profile p ON p.profileid=ps.profileid JOIN vtiger_tab t ON t.tabid=ps.tabid
WHERE ps.permissions<>0 AND t.presence IN (0,2) ORDER BY 2,3,4;
SELECT 'profile2global' kind, p.profilename, pg.globalactionid, pg.globalactionpermission FROM vtiger_profile2globalpermissions pg JOIN vtiger_profile p ON p.profileid=pg.profileid;
SELECT 'profile2field_restricted' kind, p.profilename, t.name module, f.fieldname, pf.visible, pf.readonly FROM vtiger_profile2field pf
JOIN vtiger_profile p ON p.profileid=pf.profileid JOIN vtiger_field f ON f.fieldid=pf.fieldid JOIN vtiger_tab t ON t.tabid=pf.tabid
WHERE (pf.visible<>0 OR pf.readonly<>0) AND t.presence IN (0,2) ORDER BY 2,3,4;
SELECT 'access_fields_acl' kind, p.profilename, f.fieldname, f.fieldlabel, pf.visible, pf.readonly FROM vtiger_profile2field pf
JOIN vtiger_profile p ON p.profileid=pf.profileid JOIN vtiger_field f ON f.fieldid=pf.fieldid
WHERE f.tabid=4 AND f.columnname IN ('cf_1322','cf_1324','cf_1326','cf_1328') ORDER BY 2,3;
SELECT 'def_org_field_access_fields' kind, f.fieldname, d.visible, d.readonly FROM vtiger_def_org_field d JOIN vtiger_field f ON f.fieldid=d.fieldid
WHERE f.tabid=4 AND f.columnname IN ('cf_1322','cf_1324','cf_1326','cf_1328');
SELECT 'datashare' kind, 'grp2grp' t, COUNT(*) FROM vtiger_datashare_grp2grp UNION ALL SELECT 'datashare','grp2role',COUNT(*) FROM vtiger_datashare_grp2role
UNION ALL SELECT 'datashare','grp2rs',COUNT(*) FROM vtiger_datashare_grp2rs UNION ALL SELECT 'datashare','role2group',COUNT(*) FROM vtiger_datashare_role2group
UNION ALL SELECT 'datashare','role2role',COUNT(*) FROM vtiger_datashare_role2role UNION ALL SELECT 'datashare','role2rs',COUNT(*) FROM vtiger_datashare_role2rs
UNION ALL SELECT 'datashare','rs2grp',COUNT(*) FROM vtiger_datashare_rs2grp UNION ALL SELECT 'datashare','rs2role',COUNT(*) FROM vtiger_datashare_rs2role
UNION ALL SELECT 'datashare','rs2rs',COUNT(*) FROM vtiger_datashare_rs2rs UNION ALL SELECT 'datashare','module_rel',COUNT(*) FROM vtiger_datashare_module_rel;
-- Record ownership by owner id (anonymous ids), live records only.
SELECT 'owner' kind, c.setype, CASE WHEN u.id IS NOT NULL THEN CONCAT('user#',u.id,':',u.status) WHEN g.groupid IS NOT NULL THEN CONCAT('group#',g.groupid) ELSE CONCAT('dangling#',c.smownerid) END owner, COUNT(*) n
FROM vtiger_crmentity c LEFT JOIN vtiger_users u ON u.id=c.smownerid LEFT JOIN vtiger_groups g ON g.groupid=c.smownerid WHERE c.deleted=0 GROUP BY 2,3 ORDER BY 2,3;
SELECT 'creator' kind, c.setype, CASE WHEN u.id IS NOT NULL THEN CONCAT('user#',u.id) WHEN c.smcreatorid=0 THEN '(zero)' ELSE CONCAT('dangling#',c.smcreatorid) END creator, COUNT(*) n
FROM vtiger_crmentity c LEFT JOIN vtiger_users u ON u.id=c.smcreatorid WHERE c.deleted=0 GROUP BY 2,3 ORDER BY 2,3;
