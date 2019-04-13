import json
import SalesforceMetadataModule as smm
import dicttoxml
from xml.dom.minidom import parseString

__author__ = "Damien Heiser"
__copyright__ = "Copyright 2019, Damien Heiser"
__credits__ = ["Damien Heiser"]
__version__ = "0.1"
__maintainer__ = "Damien Heiser"
__email__ = "damien@damienheiser.com"
__status__ = "Development"

# some basic default settings for this class

#### Salesforce
# _sfdcPrefix must start with a letter, less than or equal to 4 characters to prevent
#   invalid full API names over 40 characers
# all fields and objects created through this class will use this prefix
#   Detail objects will have d_ appended (i.e.) in addition to the prefix
_sfdcPrefix = 'f_'
_sfdcUsername = "your.salesforce@username.com"
_sfdcPassword = "yourSalesforcePassword"
_sfdcToken = "yourSalesforceSecurityToken"
# Set _sfdcSandbox to False to run in production
_sfdcSandbox = True
_sfdcAutoNumberDisplayMaster = 'YYYY-MM-DD-{000000}'
_sfdcAutoNumberDisplayDetail = 'YYYY-MM-DD-{000000}'

# used for xml manipulation, don't chage me <3
_item_to_none_func = lambda x: None

class FulcrumApplicationToSalesforceObject:
	sfdc = ''

	def __init__ (self):
		if len(_sfdcPrefix) > 4:
			sys.exit("_sfdcPrefix Must Be 4 or Less Characters.  Current value is " + _sfdcPrefix + " which is " + len(_sfdcPrefix) + " characters long.")
		self.sfdc = smm.SalesforceMetadataModule(_sfdcUsername, _sfdcPassword , _sfdcToken, _sfdcSandbox)
	# Determines if a string starts with a vowel

	def startsWithVowel (self, value):
		vowels = ['a','e','i','o','u','A','E','I','O','U']
		if value[0] in vowels:
			return 'Vowel'
		else:
			return 'Consonant'

	#Returns a string defining the characteristics of the field Primitive function
	def map_fulcrum_field_to_datatype (self, fieldDef):
		if fieldDef['type'] == 'TextField' and fieldDef['numeric'] == False and fieldDef['max_length'] <= 255:
			return 'Text'
		elif fieldDef['type'] == 'TextField' and fieldDef['numeric'] == False:
			return 'LongTextArea'
		elif fieldDef['type'] == 'TextField' and fieldDef['numeric'] == True and fieldDef['format'] == 'decimal':
			return 'DecimalNumber'
		elif fieldDef['type'] == 'TextField' and fieldDef['numeric'] == True and fieldDef['format'] == 'integer':
			return 'IntegerNumber'
		elif fieldDef['type'] == 'YesNoField' and fieldDef['neutral_enabled'] == False:
			return 'YesNoPicklist'
		elif fieldDef['type'] == 'YesNoField' and fieldDef['neutral_enabled'] == True:
			return 'YesNoNeutralPicklist'
		elif fieldDef['type'] == 'Section':
			return 'Section'
		elif fieldDef['type'] == 'ChoiceField' and fieldDef['multiple'] == False:
			return 'Picklist'
		elif fieldDef['type'] == 'ChoiceField' and fieldDef['multiple'] == True:
			return 'MultiSelectPicklist'
		elif fieldDef['type'] == 'ClassificationField':
			return 'ClassificationField'
		elif fieldDef['type'] == 'Repeatable':
			return 'MasterDetail'
		elif fieldDef['type'] == 'SignatureField':
			return 'Signature'
		elif fieldDef['type'] == 'PhotoField':
			return 'Photo'
		elif fieldDef['type'] == 'VideoField':
			return 'Video'
		elif fieldDef['type'] == 'AudioField':
			return 'Audio'
		elif fieldDef['type'] == 'AddressField':
			return 'Address'
		elif fieldDef['type'] == 'BarcodeField':
			return 'Barcode'
		elif fieldDef['type'] == 'HyperlinkField':
			return 'URL'
		elif fieldDef['type'] == 'RecordLinkField':
			return 'Lookup'
		elif fieldDef['type'] == 'DateTimeField':
			return 'Date'
		elif fieldDef['type'] == 'TimeField':
			return 'DateTime'

	##### Process Fulcrum Choice Lists

	## Generate Value Set Definition for status picklist field
	def fulcrum_process_status_choice_list (self, field):
		values = []
		for choice in field['choices']:
			default = False
			if choice['value'] == field['default_value']:
				default = True

			values.append ( {'default':default,
				'label':choice['label'],
				'color':choice['color'],
				'fullName':choice['value']
			})
			print '   Creating Field Value! '+ field['data_name'] + ' : ' + field['label'] +' ('+ field['type'] +') | Value : ' + choice['label']
		return values


	####

	## Generate Value Set Definition for standard picklist fields
	def fulcrum_process_choice_list (self, field):
		values = []
		for choice in field['choices']:
			default = False
			if choice['value'] == field['default_value']:
				default = True
			values.append ( {'default':default,
				'label':choice['label'],
				'fullName':choice['value'] 
			})
		return values


	## Generate Value Set Definition for YesNoFields
	def fulcrum_process_yesno_list (self, field):
		values = []

		default = False
		if field['default_value'] == field['positive']['value']:
			default = True
		values.append ( {'default':default,
				'label':field['positive']['label'],
				'fullName':field['positive']['value'],
			})

		default = False
		if field['default_value'] == field['negative']['value']:
			default = True
		values.append ( {'default':default,
				'label':field['negative']['label'],
				'fullName':field['negative']['value'],
			})

		return values

	def fulcrum_process_yesnoneutral_list (self, field):
		values = []

		default = False
		if field['default_value'] == field['positive']['value']:
			default = True
		values.append ( {'default':default,
				'label':field['positive']['label'],
				'fullName':field['positive']['value'],
			})

		default = False
		if field['default_value'] == field['negative']['value']:
			default = True
		values.append ( {'default':default,
				'label':field['negative']['label'],
				'fullName':field['negative']['value'],
			})

		default = False
		if field['default_value'] == field['neutral']['value']:
			default = True
		values.append ( {'default':default,
				'label':field['neutral']['label'],
				'fullName':field['neutral']['value'],
			})

		return values

	#### Primitive Salesforce Metadata Creation

	def salesforce_custom_field_text (self, field, length = 255):
		sfdcField = {
			'type':'Text',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'],
			'description':field['description'],
			'length':length,
			'required':field['required']
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_longtextarea (self, field):
		sfdcField = {
			'type':'LongTextArea',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'],
			'description':field['description'],
			'length':32767,
			'visibleLines':10,
			'stripMarkup':True,
			'required':field['required']
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_number (self, field, precision, scale):
		sfdcField = {
			'type':'Number',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'],
			'description':field['description'],
			'precision':precision,
			'scale':scale,
			'required':field['required'],
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +' Precision:' + str(precision) + ' Scale:' + str(scale) + ')'
		return sfdcField

	def salesforce_custom_field_decimal_number (self, field):
		return self.salesforce_custom_field_number (field, 18, 9)

	def salesforce_custom_field_integer_number (self, field):
		return self.salesforce_custom_field_number (field, 18, 0)

	def salesforce_custom_field_picklist (self, field):
		sfdcField = {
			'type':'Picklist',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'],
			'description':field['description'],
			'valueSet':{'valueSetDefinition': {'value': self.fulcrum_process_choice_list (field)}},
			'required':field['required']
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_yesno_picklist (self, field):
		sfdcField = {
			'type':'Picklist',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'],
			'description':field['description'],
			'valueSet':{'valueSetDefinition': {'value': self.fulcrum_process_yesno_list (field)}},
			'required':field['required']
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_yesnoneutral_picklist (self, field):
		sfdcField = {
			'type':'Picklist',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'],
			'description':field['description'],
			'valueSet':{'valueSetDefinition': {'value': self.fulcrum_process_yesnoneutral_list (field)}},
			'required':field['required']
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_multiselectpicklist (self, field):
		sfdcField = {
			'type':'MultiselectPicklist',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'],
			'description':field['description'],
			'valueSet':{'valueSetDefinition': {'value': self.fulcrum_process_choice_list (field)}},
			'required':field['required'],
			'visibleLines':10
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_masterdetail (self, field, parentId, parentLabel):
		  #check to see if it exists

		#sfdc.listMetadata ()

		sfdcField = {
			'type':'MasterDetail',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':parentLabel,
			'description':field['description'],
			'referenceTo':parentId,
			'relationshipLabel':field['label'] + 's',
			'relationshipName':field['data_name']
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_url (self, field):
		sfdcField = {
			'type':'Url',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'],
			'description':field['description'],
			'required':field['required']
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_lookup (self, field):
		#check to see if it exists

		#sfdc.listMetadata ()

		sfdcField = {
			'type':'Lookup',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'],
			'description':field['description'],
			'required':field['required'],
			'referenceTo':field['form_id'] + '__c',
			'relationshipLabel':field['label'] + 's',
			'relationshipName':field['data_name']
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_date (self, field):
		sfdcField = {
			'type':'Date',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'],
			'description':field['description'],
			'required':field['required']
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_datetime (self, dateField, timeField):
		#Can only be true if both compounding fields are true
		required = False
		if dateField['required'] == True and timeField['required'] == True:
			required = True
		sfdcField = {
			'type':'DateTime',
			'fullName': _sfdcPrefix + dateField['key'] + '_' + timeField['key'] + '__c',
			'label':timeField['label'],
			'description':timeField['description'],
			'required':required
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	## Helper Functions for Salesforce Special Data Types

	def salesforce_integration_field_status (self, field):
		sfdcField = {
			'type':'Picklist',
			'fullName': _sfdcPrefix + field['data_name'] + '__c',
			'label':field['label'],
			'description':field['description'],
			'valueSet':{'valueSetDefinition': {'value': self.fulcrum_process_status_choice_list (field)}},
			'required':field['required']
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	## Generates a set of fields for each address field that exists in a fulcrum record but not defined in the json
	## To prevent strange issues, all of these fields are mapped to required False, even if set to true in Fulcrum
	def salesforce_custom_field_address (self, field):
		print '   Creating Multiple Fields! ' + field['label'] +' (Address)'
		sfdcField = []
		sfdcField.append ( self.salesforce_custom_field_text ({'key':field['key'] + '_sub_thoroughfare',
			'label':field['label'] + ' Street Number',
			'required': False,
			'description': field['label'] + ' Street Number'}))

		sfdcField.append ( self.salesforce_custom_field_text ({'key':field['key'] + '_thoroughfare',
			'label':field['label'] + ' Street',
			'required': False,
			'description': field['label'] + ' Street'}))

		sfdcField.append ( self.salesforce_custom_field_text ({'key':field['key'] + '_suite',
			'label':field['label'] + ' Suite',
			'required': False,
			'description': field['label'] + ' Suite'}))

		sfdcField.append ( self.salesforce_custom_field_text ({'key':field['key'] + '_locality',
			'label':field['label'] + ' City',
			'required': False,
			'description': field['label'] + ' City'}))

		sfdcField.append ( self.salesforce_custom_field_text ({'key':field['key'] + '_sub_admin_area',
			'label':field['label'] + ' County',
			'required': False,
			'description': field['label'] + ' County'}))

		sfdcField.append ( self.salesforce_custom_field_text ({'key':field['key'] + '_admin_area',
			'label':field['label'] + ' State/Province',
			'required': False,
			'description': field['label'] + ' State/Province'}))

		sfdcField.append ( self.salesforce_custom_field_text ({'key':field['key'] + '_country',
			'label':field['label'] + ' Country',
			'required': False,
			'description': field['label'] + ' Country'}))
		return sfdcField

	#Sets an External ID Field
	def salesforce_custom_field_barcode (self, field):
		sfdcField = {
			'type':'Text',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'],
			'description':field['description'],
			'length':255,
			'required':field['required'],
			'defaultValue':field['default_value'],
			'externalId':True
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_geolocation (self, field):
		sfdcField = {
			'type':'Location',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'],
			'description':field['description'],
			'required':field['required'],
			'defaultValue':field['default_value'],
			#'precision':18,
			'scale':9
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_integration_field_fulcrum_id (self, data):
		sfdcField = {
			'type':'Text',
			'fullName': _sfdcPrefix + 'Fulcrum_Id__c',
			'label':'Fulcrum Id',
			'description':'Fulcrum Generated Record Id',
			'length':255,
			'required':False,
			'externalId':True
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_integration_field_project_id (self, data):
		sfdcField = {
			'type':'Text',
			'fullName': _sfdcPrefix + 'Fulcrum_Project_Id__c',
			'label':'Fulcrum Project Id',
			'description':'Fulcrum Generated Project Id',
			'length':255,
			'required':False,
			'externalId':True
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_integration_field_assigned_to (self, data):
		sfdcField = {
			'type':'Text',
			'fullName': _sfdcPrefix + 'Assigned_To__c',
			'label':'Assigned To',
			'description':'Record is assigned to this person in Fulcrum',
			'length':255,
			'required':False,
			'externalId':False
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_integration_field_assigned_to_id (self, data):
		sfdcField = {
			'type':'Text',
			'fullName': _sfdcPrefix + 'Fulcrum_Assigned_To_Id__c',
			'label':"Fulcrum Assigned To Id",
			'description':'The Fulcrum User ID that this record is Assigned To',
			'length':255,
			'required':False,
			'externalId':True
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_integration_field_project_id_lookup (self, data):
		sfdcField = {
			'type':'Lookup',
			'fullName': _sfdcPrefix + 'Fulcrum_Project__c',
			'label':"Fulcrum Project",
			'description':'Link to Fulcrum Project Object for reporting purposes',
			'required':False,
			'referenceTo': _sfdcPrefix + 'Fulcrum_Project__c',
			'relationshipLabel':'Fulcrum Projects',
			'relationshipName':'fulcrum_projects'
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_integration_field_location (self, data):
		sfdcField = {
			'type':'Location',
			'fullName': _sfdcPrefix + 'Location__c',
			'label':'Location',
			'description':'Geolocation Coordinates',
			'required':data['geometry_required'],
			#'precision':18,
			'scale':9
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	# Take an array of values representing fields
	def fulcrum_map_title_field_keys_to_salesforce_fields (self, array):
		i = 0
		for value in array:
			if i == 0:
				sfdcTitle = _sfdcPrefix + value + '__c'
			else:
				sfdcTitle += ' + " | " +' + _sfdcPrefix + value + '__c'
			i += 1
		sfdcTitle.replace('-', '_')
		return sfdcTitle

	def fulcrum_title_to_salesforce_formula (self, data):
		sfdcField = {
			'type':'Text',
			'fullName': _sfdcPrefix + 'Title__c',
			'label':'Title',
			'description':'Title as displayed in Fulcrum',
			'formula':self.fulcrum_map_title_field_keys_to_salesforce_fields (data['title_field_keys'])
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	# Determines the type of field, and generates the field structure of the object
	def fulcrum_to_salesforce_field_elements (self, elements):
		sfdcFields = []
		i = 0
		for field in elements:
			fieldType = self.map_fulcrum_field_to_datatype (field)
			if fieldType == 'Text':
				sfdcFields.append ( self.salesforce_custom_field_text (field) )
			elif fieldType == 'LongTextArea':
				sfdcFields.append ( self.salesforce_custom_field_longtextarea (field) )
			elif fieldType == 'DecimalNumber':
				sfdcFields.append ( self.salesforce_custom_field_decimal_number (field) )
			elif fieldType == 'IntegerNumber':
				sfdcFields.append ( self.salesforce_custom_field_integer_number (field) )
			elif fieldType == 'YesNoPicklist':
				sfdcFields.append ( self.salesforce_custom_field_yesno_picklist (field) )
			elif fieldType == 'YesNoNeutralPicklist':
				sfdcFields.append ( self.salesforce_custom_field_yesnoneutral_picklist (field) )
			elif fieldType == 'Section':
				#A section is a collection of fields encapulated within an 'elements' array within the field
				#This should extend the number of fields in the array
				sfdcFields.extend ( self.fulcrum_to_salesforce_field_elements (field['elements']) )
			elif fieldType == 'Picklist':
				sfdcFields.append ( self.salesforce_custom_field_picklist (field) )
			elif fieldType == 'MultiSelectPicklist':
				sfdcFields.append ( self.salesforce_custom_field_multiselectpicklist (field) )
			#elif fieldType == 'ClassificationFieldPicklist':
				#Do Nothing For The Time Being, this is it's own integration itself
			elif fieldType == 'Address':
				sfdcFields.extend ( self.salesforce_custom_field_address (field) )
			elif fieldType == 'Barcode':
				sfdcFields.append ( self.salesforce_custom_field_barcode (field) )
			elif fieldType == 'URL':
				sfdcFields.append ( self.salesforce_custom_field_url (field) )
			elif fieldType == 'Lookup':
				#must verify that the object exists in salesforce before lookup is permitted
				sfdcFields.append ( self.salesforce_custom_field_lookup (field) )
			elif fieldType == 'Date':
				#must verify that the object exists in salesforce before lookup is permitted
				sfdcFields.append ( self.salesforce_custom_field_date (field) )
			# Date time is special.  There is no Time field in Salesforce.
			# Instead, if we encouter this type, do a child interation of elements
			# To determine if there is a Date field directly preceeding this Date Time field
			# This mapping will duplicate dates Twice if a Time is specificed directly below
			# This is a desired functionality trait (not a bug seriously I thought about this)
			elif fieldType == 'DateTime':
				j = 0
				for iterateForDateField in elements:
					isDateFieldType = self.map_fulcrum_field_to_datatype (iterateForDateField)
					if isDateFieldType == 'Date':
						# Check to see that the Date field exists before this Time field to pair them
						if i-j == 1:
							sfdcFields.append ( self.salesforce_custom_field_datetime (iterateForDateField, field) )
					j += 1
			elif fieldType == 'Photo' or fieldType == 'Video' or fieldType == 'Audio' or fieldType == 'Signature' or fieldType == 'MasterDetail':
				sfdcFields.append ( self.salesforce_custom_field_longtextarea (field) )
			i += 1

		return sfdcFields

	#Generates all of the repeatable sections on the object as details
	def fulcrum_repeatable_sections_as_sfdc_master_detail (self, data, parentId, parentLabel, action):
		for field in data['elements']:
			fieldType = self.map_fulcrum_field_to_datatype (field)
			if fieldType == 'MasterDetail':
				#Create New Object with a Master Detail Relationship
				self.construct_fulcrum_sfdc_object_child (field, parentId, parentLabel, action)

	# Construct Master Object
	def construct_fulcrum_sfdc_object (self, data, action='create', autonumber=True):
		print 'Creating Object! ' + data['name'] +''
		sfdcFields = [
			self.salesforce_integration_field_fulcrum_id (data),
			self.salesforce_integration_field_location (data),
			self.salesforce_integration_field_assigned_to (data),
			self.salesforce_integration_field_assigned_to_id (data),
			self.salesforce_integration_field_project_id (data),
			self.salesforce_integration_field_project_id_lookup (data),
			self.fulcrum_title_to_salesforce_formula (data),
			self.salesforce_custom_field_integer_number ({'key':'created_duration', 'label':'Created Duration', 'description':'Time to initially create this record in sections','required':False}),
			self.salesforce_custom_field_integer_number ({'key':'updated_duration', 'label':'Updated Duration', 'description':'Time spent updating this updating','required':False}),
			self.salesforce_custom_field_integer_number ({'key':'edited_duration', 'label':'Edited Duration', 'description':'Time spent editing this record','required':False})
		]

		xml = ''

		if 'status_field' in data.keys():
			if data['status_field']['enabled'] == True:
				sfdcFields.append (self.salesforce_integration_field_status (data['status_field']))

		sfdcFields.extend(self.fulcrum_to_salesforce_field_elements (data['elements']))

		for sfdcField in sfdcFields:
			xml += dicttoxml.dicttoxml({'fields': sfdcField}, item_func=_item_to_none_func, attr_type=False, root=False).replace('<value>','').replace('</value>','').replace('<None>','<value>').replace('</None>','</value>')

		if autonumber == True:
			sfdcObject = {'label':data['name'],
				'pluralLabel':data['name'] + 's',
				'fullName': _sfdcPrefix + data['id'].replace('-','_') + '__c',
				'sharingModel':'ReadWrite',
				'deploymentStatus':'Deployed',
				'startsWith':self.startsWithVowel(data['name']),
				'description':data['description'],
				'enableActivities':True,
				'enableHistory':True,
				'enableReports':True,
				'enableSearch':True,
				'nameField':{'type':'AutoNumber',
					'label':data['name'],
					'startingNumber':0,
					'displayFormat':_sfdcAutoNumberDisplayMaster}
				}
		else:
			sfdcObject = {'label':data['name'],
				'pluralLabel':data['name'] + 's',
				'fullName': _sfdcPrefix + data['id'].replace('-','_') + '__c',
				'sharingModel':'ReadWrite',
				'deploymentStatus':'Deployed',
				'startsWith':self.startsWithVowel(data['name']),
				'description':data['description'],
				'enableActivities':True,
				'enableHistory':True,
				'enableReports':True,
				'enableSearch':True,
				'nameField':{'type':'Text',
					'label':data['name']}
				}

		xml += dicttoxml.dicttoxml(sfdcObject, item_func=_item_to_none_func, attr_type=False, root=False).replace('<value>','').replace('</value>','').replace('<None>','<value>').replace('</None>','</value>')

		if action == 'create':
			print parseString(dicttoxml.dicttoxml (self.sfdc.createMetadata (xml))).toprettyxml()
		elif action == 'update':
			print parseString(dicttoxml.dicttoxml (self.sfdc.updateMetadata (xml))).toprettyxml()
		else:
			print '...TESTING... Use action create or update to commit. ...TESTING...'
			print parseString(xml).toprettyxml()
			print '...TESTING... Use action create or update to commit. ...TESTING...'
		parentId = _sfdcPrefix + data['id'].replace('-','_') + '__c'
		parentLabel = data['name']
		self.fulcrum_repeatable_sections_as_sfdc_master_detail (data, parentId, parentLabel, action)

	## Constructs Detail Objects
	def construct_fulcrum_sfdc_object_child (self, data, parentId, parentLabel, action = 'create'):
		print 'Creating ' + parentLabel + ' Detail Object! ' + data['label'] +''
		sfdcFields = [
			self.salesforce_integration_field_fulcrum_id (data),
			self.salesforce_integration_field_location (data),
			self.fulcrum_title_to_salesforce_formula (data),
			self.salesforce_custom_field_masterdetail (data, parentId, parentLabel),
		]

		xml = ''

		if 'status_field' in data.keys():
			if data['status_field']['enabled'] == True:
				sfdcFields.append (self.salesforce_integration_field_status (data['status_field']))

		sfdcFields.extend (self.fulcrum_to_salesforce_field_elements (data['elements']))

		for sfdcField in sfdcFields:
			# Leave the .replace on here.  It's to get rid of a duplicate parent Item keys for nested tables
			xml += dicttoxml.dicttoxml({'fields': sfdcField}, item_func=_item_to_none_func, attr_type=False, root=False).replace('<value>','').replace('</value>','').replace('<None>','<value>').replace('</None>','</value>')

		sfdcObject = {'label':data['label'],
			'pluralLabel':data['label'] + 's',
			'fullName': _sfdcPrefix + "d_" + data['key'] + '__c',
			'sharingModel':'ControlledByParent',
			'deploymentStatus':'Deployed',
			'startsWith':self.startsWithVowel(data['label']),
			'description':data['description'],
			'enableActivities':True,
			'enableHistory':True,
			'enableReports':True,
			'enableSearch':True,
			'nameField':{'type':'AutoNumber',
				'label':data['label'],
				'startingNumber':0,
				'displayFormat':_sfdcAutoNumberDisplayDetail}
			}

		# Leave the .replace on here.  It's to get rid of a duplicate parent Item keys for nested tables
		xml += dicttoxml.dicttoxml(sfdcObject, item_func=_item_to_none_func, attr_type=False, root=False).replace('<value>','').replace('</value>','').replace('<None>','<value>').replace('</None>','</value>')

		if action == 'create':
			print parseString(dicttoxml.dicttoxml (self.sfdc.createMetadata (xml))).toprettyxml()
		elif action == 'update':
			print parseString(dicttoxml.dicttoxml (self.sfdc.updateMetadata (xml))).toprettyxml()
		else:
			print '...TESTING... Use action create or update to commit. ...TESTING...'
			print parseString(xml).toprettyxml()
			print '...TESTING... Use action create or update to commit. ...TESTING...'
