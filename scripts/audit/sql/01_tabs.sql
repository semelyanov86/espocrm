-- Modules with live/deleted record counts and field counts.
SELECT t.tabid, t.name, t.presence, t.isentitytype, t.customized, IFNULL(t.parent,'') parent, IFNULL(t.version,'') version,
  (SELECT COUNT(*) FROM vtiger_crmentity c WHERE c.setype=t.name AND c.deleted=0) live,
  (SELECT COUNT(*) FROM vtiger_crmentity c WHERE c.setype=t.name AND c.deleted=1) deleted,
  (SELECT COUNT(*) FROM vtiger_field f WHERE f.tabid=t.tabid) nfields,
  (SELECT COUNT(*) FROM vtiger_field f WHERE f.tabid=t.tabid AND f.generatedtype=2) ncustom
FROM vtiger_tab t ORDER BY t.tabid;
