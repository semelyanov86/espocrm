-- PBXManager history shape (no numbers, no URLs beyond host/scheme pattern).
SELECT 'uuid_shape' k, REGEXP_REPLACE(REGEXP_REPLACE(sourceuuid,'[0-9]','9'),'[a-f]','x') shape, COUNT(*) n FROM vtiger_pbxmanager GROUP BY 2 ORDER BY 3 DESC LIMIT 5;
SELECT 'pbx_month' k, DATE_FORMAT(p.starttime,'%Y-%m') ym, COUNT(*) n, SUM(p.direction='inbound') inbound, SUM(p.direction='outbound') outbound,
  SUM(p.recordingurl IS NOT NULL AND p.recordingurl<>'') with_rec, SUM(p.sp_recordingurl IS NOT NULL AND p.sp_recordingurl<>'') with_sp_rec
FROM vtiger_pbxmanager p JOIN vtiger_crmentity c ON c.crmid=p.pbxmanagerid AND c.deleted=0 GROUP BY 2 ORDER BY 2;
SELECT 'pbx_status' k, p.direction, p.callstatus, COUNT(*) n, SUM(p.billduration>0) billed, ROUND(AVG(p.totalduration)) avg_total FROM vtiger_pbxmanager p GROUP BY 2,3 ORDER BY 2,3;
SELECT 'pbx_rec_pattern' k, REGEXP_REPLACE(REGEXP_SUBSTR(p.recordingurl,'^[a-z]+://[^/]+'),'[0-9]','9') host_pattern, COUNT(*) n FROM vtiger_pbxmanager p WHERE p.recordingurl<>'' GROUP BY 2;
SELECT 'pbx_rec_path_shape' k, REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_SUBSTR(p.recordingurl,'^[a-z]+://[^/]+(/[^?]*)?'),'[0-9]','9'),'^[a-z]+://[^/]+','') path_shape,
  REGEXP_SUBSTR(p.recordingurl,'[?&][a-zA-Z_]+=') first_param, COUNT(*) n FROM vtiger_pbxmanager p WHERE p.recordingurl<>'' GROUP BY 2,3 ORDER BY 4 DESC LIMIT 10;
SELECT 'pbx_fields' k, p.gateway, IFNULL(p.sp_voip_provider,'') provider, COUNT(*) n, SUM(p.sourceuuid<>'') uuid_nz, SUM(p.sourceuuid REGEXP '^[0-9]+\\.[0-9]+$') uuid_asterisk_like,
  SUM(p.customernumber<>'') custnum_nz, SUM(p.customertype<>'') custtype_nz, SUM(p.incominglinename<>'') line_nz, SUM(p.sp_called_from_number<>'') from_nz,
  SUM(p.sp_called_to_number<>'') to_nz, SUM(p.sp_is_recorded<>'') is_rec_nz, SUM(p.sp_recorded_call_id<>'') rec_id_nz, SUM(p.sp_is_local_cached=1) cached, MIN(p.starttime), MAX(p.starttime)
FROM vtiger_pbxmanager p GROUP BY 2,3;
SELECT 'pbx_user_map' k, CONCAT('user#',u.id) owner, COUNT(*) n FROM vtiger_pbxmanager p LEFT JOIN vtiger_users u ON u.id=p.user GROUP BY 2;
SELECT 'pbx_customertype' k, p.customertype, COUNT(*) n FROM vtiger_pbxmanager p GROUP BY 2;
SELECT 'pbx_gateway' k, g.id, g.gateway, JSON_KEYS(IF(JSON_VALID(g.parameters), g.parameters, '{}')) param_keys FROM vtiger_pbxmanager_gateway g;
SELECT 'voip_settings' k, provider_name, field_name, (field_value IS NOT NULL AND field_value<>'') has_value FROM vtiger_sp_voipintegration_settings ORDER BY 2,3;
SELECT 'voip_default_provider' k, default_provider FROM vtiger_sp_voip_default_provider;
SELECT 'voip_options' k, name, (value IS NOT NULL AND value<>'') has_value FROM vtiger_sp_voipintegration_options;
SELECT 'phonelookup' k, setype, fieldname, COUNT(*) n FROM vtiger_pbxmanager_phonelookup GROUP BY 2,3;
SELECT 'callpopup' k, COUNT(*) n, SUM(comment IS NOT NULL AND comment<>'') comment_nz, SUM(client_type<>'') client_type_nz, SUM(firstname<>'' OR lastname<>'') name_nz, SUM(accountname<>'') accname_nz FROM vtiger_sp_callpopup;
SELECT 'user_extensions' k, CONCAT('user#',u.id) uid, (e.asterisk_extension IS NOT NULL AND e.asterisk_extension<>'') has_ext, IFNULL(e.use_asterisk,'') use_asterisk,
  (u.phone_crm_extension IS NOT NULL AND u.phone_crm_extension<>'') has_crm_ext FROM vtiger_users u LEFT JOIN vtiger_asteriskextensions e ON e.userid=u.id;
