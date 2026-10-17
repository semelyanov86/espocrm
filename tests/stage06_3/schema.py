"""Tables of the stage-06.3 modules for a synthetic mini-Vtiger (real column names and types, a subset of the columns
is enough: the import reads the columns a table has). Shared by the acceptance tests of stages 06.2 and 06.3.
"""

ADDRESS = ("bill_city VARCHAR(30), bill_code VARCHAR(30), bill_country VARCHAR(30), bill_state VARCHAR(30), "
           "bill_street VARCHAR(250), bill_pobox VARCHAR(30)")
SHIP = ("ship_city VARCHAR(30), ship_code VARCHAR(30), ship_country VARCHAR(30), ship_state VARCHAR(30), "
        "ship_street VARCHAR(250), ship_pobox VARCHAR(30)")
DOCUMENT = ("subject VARCHAR(100), contactid INT, accountid INT, adjustment DECIMAL(25,8), subtotal DECIMAL(25,8), "
            "total DECIMAL(25,8), pre_tax_total DECIMAL(25,8), taxtype VARCHAR(25), discount_percent DECIMAL(25,3), "
            "discount_amount DECIMAL(25,8), s_h_amount DECIMAL(25,8), s_h_percent INT, currency_id INT, "
            "conversion_rate DECIMAL(10,3), compound_taxes_info TEXT, spcompany VARCHAR(200), region_id INT")

COLUMNS_063 = {
    "vtiger_vendor": "vendorid INT PRIMARY KEY, vendor_no VARCHAR(100), vendorname VARCHAR(100), phone VARCHAR(100), "
                     "email VARCHAR(100), website VARCHAR(100)",
    "vtiger_vendorcf": "vendorid INT PRIMARY KEY, cf_1206 VARCHAR(15)",
    "vtiger_products": "productid INT PRIMARY KEY, product_no VARCHAR(100), productname VARCHAR(100), "
                       "productcode VARCHAR(40), discontinued INT, unit_price DECIMAL(25,8), usageunit VARCHAR(200), "
                       "qtyinstock DECIMAL(25,3), currency_id INT",
    "vtiger_productcf": "productid INT PRIMARY KEY",
    "vtiger_service": "serviceid INT PRIMARY KEY, service_no VARCHAR(100), servicename VARCHAR(50), "
                      "servicecategory VARCHAR(200), qty_per_unit DECIMAL(11,2), unit_price DECIMAL(25,8), "
                      "discontinued INT, service_usageunit VARCHAR(200), website VARCHAR(100), currency_id INT",
    "vtiger_servicecf": "serviceid INT PRIMARY KEY, cf_billable_time_tracker VARCHAR(3)",
    "vtiger_quotes": f"quoteid INT PRIMARY KEY, quote_no VARCHAR(100), potentialid INT, quotestage VARCHAR(200), "
                     f"validtill DATE, inventorymanager INT, terms_conditions TEXT, {DOCUMENT}",
    "vtiger_quotescf": "quoteid INT PRIMARY KEY, tax DECIMAL(25,3)",
    "vtiger_quotesbillads": f"quotebilladdressid INT PRIMARY KEY, {ADDRESS}",
    "vtiger_quotesshipads": f"quoteshipaddressid INT PRIMARY KEY, {SHIP}",
    "vtiger_salesorder": f"salesorderid INT PRIMARY KEY, salesorder_no VARCHAR(100), potentialid INT, quoteid INT, "
                         f"duedate DATE, sostatus VARCHAR(200), enable_recurring INT, terms_conditions TEXT, {DOCUMENT}",
    "vtiger_salesordercf": "salesorderid INT PRIMARY KEY, tax DECIMAL(25,3)",
    "vtiger_sobillads": f"sobilladdressid INT PRIMARY KEY, {ADDRESS}",
    "vtiger_soshipads": f"soshipaddressid INT PRIMARY KEY, {SHIP}",
    "vtiger_invoice_recurring_info": "salesorderid INT PRIMARY KEY, recurring_frequency VARCHAR(200), "
                                     "start_period DATE, end_period DATE",
    "vtiger_invoice": f"invoiceid INT PRIMARY KEY, invoice_no VARCHAR(100), salesorderid INT, invoicedate DATE, "
                      f"duedate DATE, invoicestatus VARCHAR(200), sp_act_id INT, received DECIMAL(25,8), "
                      f"balance DECIMAL(25,8), potential_id VARCHAR(100), customerno VARCHAR(100), "
                      f"terms_conditions TEXT, {DOCUMENT}",
    "vtiger_invoicecf": "invoiceid INT PRIMARY KEY, tax DECIMAL(25,3)",
    "vtiger_invoicebillads": f"invoicebilladdressid INT PRIMARY KEY, {ADDRESS}",
    "vtiger_invoiceshipads": f"invoiceshipaddressid INT PRIMARY KEY, {SHIP}",
    "vtiger_sp_act": f"actid INT PRIMARY KEY, act_no VARCHAR(100), actdate DATE, sp_actstatus VARCHAR(200), {DOCUMENT}",
    "vtiger_sp_actcf": "actid INT PRIMARY KEY",
    "vtiger_sp_actbillads": f"actbilladdressid INT PRIMARY KEY, {ADDRESS}",
    "vtiger_sp_actshipads": f"actshipaddressid INT PRIMARY KEY, {SHIP}",
    "vtiger_inventoryproductrel": "id INT, productid INT, sequence_no INT, quantity DECIMAL(25,3), "
                                  "listprice DECIMAL(27,8), discount_percent DECIMAL(7,3), discount_amount DECIMAL(27,8), "
                                  "comment TEXT, description TEXT, incrementondel INT, lineitem_id INT PRIMARY KEY, "
                                  "tax1 DECIMAL(7,3), tax2 DECIMAL(7,3), tax3 DECIMAL(7,3), purchase_cost DECIMAL(27,8), "
                                  "margin DECIMAL(27,8)",
    "sp_payments": "payid INT PRIMARY KEY, pay_no VARCHAR(100), pay_date DATE, pay_details VARCHAR(255), "
                   "pay_type VARCHAR(100), payer INT, doc_no INT, related_to INT, type_payment VARCHAR(100), "
                   "amount DECIMAL(25,8), spstatus VARCHAR(200), spcompany VARCHAR(200)",
    "sp_paymentscf": "payid INT PRIMARY KEY, cf_1198 BIGINT, cf_1204 VARCHAR(100), cf_1380 VARCHAR(3)",
    "vtiger_notes": "notesid INT PRIMARY KEY, note_no VARCHAR(100), title VARCHAR(50), filename VARCHAR(200), "
                    "notecontent TEXT, folderid INT, filetype VARCHAR(50), filelocationtype VARCHAR(5), "
                    "filedownloadcount INT, filestatus INT, filesize INT, fileversion VARCHAR(50)",
    "vtiger_notescf": "notesid INT PRIMARY KEY, cf_for_field VARCHAR(100)",
    "vtiger_attachmentsfolder": "folderid INT PRIMARY KEY, foldername VARCHAR(200), description VARCHAR(250), "
                                "createdby INT, sequence INT",
    "vtiger_attachments": "attachmentsid INT PRIMARY KEY, name VARCHAR(255), description TEXT, type VARCHAR(100), "
                          "path TEXT, subject VARCHAR(255)",
    "vtiger_salesmanattachmentsrel": "smid INT, attachmentsid INT",
    "vtiger_faq": "id INT PRIMARY KEY, faq_no VARCHAR(100), product_id VARCHAR(100), question TEXT, answer TEXT, "
                  "category VARCHAR(200), status VARCHAR(200)",
    "vtiger_faqcf": "faqid INT PRIMARY KEY",
    "vtiger_emaildetails": "emailid INT PRIMARY KEY, from_email VARCHAR(50), to_email TEXT, cc_email TEXT, "
                           "bcc_email TEXT, idlists TEXT, email_flag VARCHAR(50)",
    "vtiger_email_track": "crmid INT, mailid INT, access_count INT, click_count INT",
    "vtiger_sp_consignment": "consignmentid INT PRIMARY KEY, consignment_no VARCHAR(100), subject VARCHAR(255), "
                             "invoiceid INT, accountid INT, consignmentdate DATE, total DECIMAL(25,8), "
                             "compound_taxes_info TEXT",
    "vtiger_sp_consignmentcf": "consignmentid INT PRIMARY KEY",
    "vtiger_sp_consignmentbillads": f"consignmentbilladdressid INT PRIMARY KEY, {ADDRESS}",
    "vtiger_sp_consignmentshipads": f"consignmentshipaddressid INT PRIMARY KEY, {SHIP}",
    "vtiger_servicecontracts": "servicecontractsid INT PRIMARY KEY, subject VARCHAR(100), contract_no VARCHAR(100), "
                               "sc_related_to INT",
    "vtiger_servicecontractscf": "servicecontractsid INT PRIMARY KEY",
    "vtiger_assets": "assetsid INT PRIMARY KEY, asset_no VARCHAR(30), assetname VARCHAR(100), account INT, product INT",
    "vtiger_assetscf": "assetsid INT PRIMARY KEY",
    "vtiger_jivosite": "jivositeid INT PRIMARY KEY, chatid INT, messages VARCHAR(100), relatedleads VARCHAR(100)",
    "vtiger_jivositecf": "jivositeid INT PRIMARY KEY",
    "vtiger_jvmes": "jvmesid INT PRIMARY KEY, message VARCHAR(500), relatedjivo VARCHAR(100)",
    "vtiger_jvmescf": "jvmesid INT PRIMARY KEY",
    "vtiger_organizationdetails": "organization_id INT PRIMARY KEY, organizationname VARCHAR(60), logoname VARCHAR(50), "
                                  "company VARCHAR(200)",
    "vtiger_modentity_num": "num_id INT PRIMARY KEY, semodule VARCHAR(100), prefix VARCHAR(50), start_id VARCHAR(50), "
                            "cur_id VARCHAR(50), active VARCHAR(2), spcompany VARCHAR(200)",
    # stage 07.2: the Vtiger call history (tests/stage07_2 fills them; empty for the earlier stages)
    "vtiger_pbxmanager": "pbxmanagerid INT PRIMARY KEY, direction VARCHAR(10), callstatus VARCHAR(20), "
                         "starttime DATETIME, endtime DATETIME, totalduration INT, billduration INT, "
                         "recordingurl VARCHAR(200), sourceuuid VARCHAR(100), gateway VARCHAR(20), customer VARCHAR(100), "
                         "user VARCHAR(100), customernumber VARCHAR(100), customertype VARCHAR(100), "
                         "incominglinename VARCHAR(100)",
    "vtiger_sp_callpopup": "popupid INT PRIMARY KEY, callid INT, call_no VARCHAR(255), status TINYINT, "
                           "firstname VARCHAR(255), lastname VARCHAR(255), client_type VARCHAR(255), comment TEXT, "
                           "accountname VARCHAR(255)",
}
# columns of vtiger_activity the archived e-mails use (beyond the calendar's)
ACTIVITY_EXTRA = "semodule VARCHAR(20), notime VARCHAR(3), sendnotification VARCHAR(3), visibility VARCHAR(50)"
