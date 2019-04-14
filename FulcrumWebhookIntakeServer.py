from klein import run, route
import json
import FulcrumApplicationToSalesforceObject as fatso

_webhookServerPort = 8080

#### Salesforce parameters
_sfdcPrefix = 'f_'
_sfdcUsername = "your.salesforce@username.com"
_sfdcPassword = "yourSalesforcePassword"
_sfdcToken = "yourSalesforceSecurityToken"
_sfdcSandbox = True

# Setup Fulcrum Webooks to hit http://yourdomain.com/_routeURL
_routeURI = 'fulcrumApp/webHook/Receipt'

### Web sever accept
@route('/'+_routeURI, methods=['POST'])

def do_post(request):
	content = json.loads(request.content.read())
	print request.content.read()

	if content['type'] == 'form.create':
		print 'Form Create'
		#Connect to Salesforce
		fulcrumToSalesforce = fatso.FulcrumApplicationToSalesforceObject ()
		#Create Object
		fulcrumToSalesforce.construct_fulcrum_sfdc_object (content['data'], 'create')
	elif content['type'] == 'form.update':
		print 'Form Update'
		fulcrumToSalesforce = fatso.FulcrumApplicationToSalesforceObject ()
		fulcrumToSalesforce.construct_fulcrum_sfdc_object (content['data'], 'create')
		fulcrumToSalesforce.construct_fulcrum_sfdc_object (content['data'], 'update')

run('0.0.0.0', _webhookServerPort)
