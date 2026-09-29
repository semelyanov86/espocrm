-- Field metadata (labels and types only, no record values).
SELECT f.tabid, t.name module, f.fieldid, f.tablename, f.columnname, f.fieldname,
  REPLACE(REPLACE(f.fieldlabel,'\t',' '),'\n',' ') fieldlabel, f.uitype, f.typeofdata, f.generatedtype, f.presence,
  f.displaytype, f.readonly, f.quickcreate, f.masseditable, IFNULL(b.blocklabel,'') blocklabel, f.sequence
FROM vtiger_field f JOIN vtiger_tab t ON t.tabid=f.tabid
LEFT JOIN vtiger_blocks b ON b.blockid=f.block
ORDER BY f.tabid, f.block, f.sequence;
