import json
import FulcrumApplicationToSalesforceObject as fts
from fulcrum import Fulcrum
import requests

_sfdcPrefix = 'f_'
_sfdcUsername = "your.salesforce@username.com"
_sfdcPassword = "yourSalesforcePassword"
_sfdcToken = "yourSalesforceSecurityToken"
_sfdcSandbox = True
_fulcrumXApiToken = "yourFulcrumAPIToken"

### Don't change anything below this point
_fulcrumBaseURL = 'https://api.fulcrumapp.com/api/v2/'

fulcrum = Fulcrum(key=_fulcrumXApiToken)
fulcrumToSalesforce = fts.FulcrumApplicationToSalesforceObject ()

# Get All Fulcrum Applications
url = _fulcrumBaseURL + 'forms.json'
headers = {'X-ApiToken': _fulcrumXApiToken}
r = requests.get(url, headers=headers)
fulcrumForm = r.json()

# Create new objects for each application
for application in fulcrumForm['forms']:
	sfdcObjectId = fulcrumToSalesforce.construct_fulcrum_sfdc_object (application, 'create')

# Run through a second time to allow new Lookup relationships to be discovered
for application in fulcrumForm['forms']:
	sfdcObjectId = fulcrumToSalesforce.construct_fulcrum_sfdc_object (application, 'create')

# Make one more complete pass through in order to make any metadata changes that may have gone through since initial load
for application in fulcrumForm['forms']:
	sfdcObjectId = fulcrumToSalesforce.construct_fulcrum_sfdc_object (application, 'update')
