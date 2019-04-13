import json
import FulcrumApplicationToSalesforceObject as fts
from fulcrum import Fulcrum

_sfdcPrefix = 'f_'
_sfdcUsername = "your.salesforce@username.com"
_sfdcPassword = "yourSalesforcePassword"
_sfdcToken = "yourSalesforceSecurityToken"
_sfdcSandbox = True
_fulcrumXApiToken = "yourFulcrumAPIToken"
#The specific Fulcrum Application Form you would like to create in salesforce
_fulcrumFormId = "yourFulcumApplicationID"

fulcrum = Fulcrum(key=_fulcrumXApiToken)
fulcrumToSalesforce = fts.FulcrumApplicationToSalesforceObject ()

# Get Individual Fulcrum Form Fulcrum Applications
fulcrumForm = fulcrum.form.find(_fulcrumFormId)

# Update Salesforce Object From Fulcrum Form
fulcrumToSalesforce.construct_fulcrum_sfdc_object (fulcrumForm, 'update')
