import json
import SalesforceMetadataModule as smm
import dicttoxml
from xml.dom.minidom import parseString
from fulcrum import Fulcrum
import re
import collections
import time
import datetime

from simple_salesforce import Salesforce
from simple_salesforce import SFType

### Some reminders.  You'll need to edit your profile, or create a permission set,
### To enable visibility of these forms.  Salesforce permissions still apply.  This script
### Will not automatically enable read/edit permissions.  So if you use the 
### FulcrumRecordToSalesforceRecord class, you'll get a ton of field not exisiting errors
### and get frustrated.
###
### TL;DR: CHECK YOUR CRED ON NEW OBJECTS AND FIELDS~
###
### Update, a Permission set for the Master Object and Child Objects created.  You will
### need to update the permisson set to enable Junction objects, or other objects created
### Recursively.

# some basic default settings for this class

#### Salesforce
# _sfdcPrefix must start with a letter, less than or equal to 4 characters to prevent
#   invalid full API names over 40 characers
# all fields and objects created through this class will use this prefix
#   Detail objects will have d_ appended (i.e.) in addition to the prefix
_sfdcPrefix = 'f_'
_sfdcUsername = ""
_sfdcPassword = ""
_sfdcToken = ""
# Set _sfdcSandbox to False to run in production
_sfdcSandbox = True
_sfdcAutoNumberDisplayMaster = '{YYYY}-{MM}-{DD}-{000000}'
_sfdcAutoNumberDisplayDetail = '{YYYY}-{MM}-{DD}-{000000}'

_fulcrumXApiToken = ""
_fulcrumBaseURL = 'https://api.fulcrumapp.com/api/v2/'

__author__ = "Damien Heiser"
__copyright__ = "Copyright 2019, Damien Heiser, Burning Man Project"
__credits__ = ["Damien Heiser"]
__version__ = "0.5"
__maintainer__ = "Damien Heiser"
__email__ = "damien.heiser@burningman.org, damien@damienheiser.com"
__status__ = "Development"
__Changelog01__ = "Initial Release"
__Changelog02__ = """Added fields to object creation that weren't in the form model but 
				   	 found in the record model. 
				   	 Fixed Bug in Address Field Mapping. 
				   	 Time Text field created if not pared with a Date.
				   	 Fixed lots of text labels. 
				   	 Automated Child Relationship Names With Field Key Affixed with _d. 
				   	 Fixed Lookup Relationship Creation
				   	 Set Fulcrum ID field to Unique to prevent accidental duplication! <3
				   	 Set Fulcrum ID field to Required to prevent accidental creation of 
				   	 	non Fulcrum Records, other methods should be used to communicate 
				   	 	to fulcrum
				   	 You can change the metadata below based on your preferences, have fun.
				   	 Title Formulas automatically generate
				   	 Junction Objects for Record Lookups with Multiple Records
				   	 Append First 13 Characters of FormID to any Junction/Detail Object
				   	 Feature Complete?"""
__Changelog03__	= """Various mapping errors, concatenation fixes, and bug fixes."""
__Changelog04__ = """Creates all related junction objects recursively.
					 Creates Tab for Application Object
					 Creates Tabs for related Applications through Junction Objects
					 Creates Permission Set for Primary Application and related Direct Objects"""
__Changelog05__ = """Add Fulcrum ID to Content Version"""

# used for xml manipulation, don't chage me <3
_item_to_none_func = lambda x: None

class FulcrumApplicationToSalesforceObject:
	sfdc = smm.SalesforceMetadataModule(_sfdcUsername, _sfdcPassword , _sfdcToken, _sfdcSandbox)
	fulcrum = Fulcrum(key=_fulcrumXApiToken)

	def __init__ (self):
		self.sfdcPermissionSetObjectPermissions = []
		self.sfdcPermissionSetFieldPermissions = []
		self.sfdcPermissionSetTabSettings = []
		self.sfdcPermissionSetTabCreated = False
		if len(_sfdcPrefix) > 4:
			sys.exit("_sfdcPrefix Must Be 4 or Less Characters.  Current value is " + _sfdcPrefix + " which is " + len(_sfdcPrefix) + " characters long.")

	# Determines if a string starts with a vowel
	def startsWithVowel (self, value):
		vowels = ['a','e','i','o','u','A','E','I','O','U']
		if value[0] in vowels:
			return 'Vowel'
		else:
			return 'Consonant'

	#checks to see if a value exists in a key
	def checkKey(self, dictionary, key):
		try:
			if key in dictionary.keys(): 
				return True
			else:
				return False
		except KeyError:
	   		return False

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
			if fieldDef['allow_multiple_records'] == True:
				return 'Junction'
			else:
				return 'Lookup'
		elif fieldDef['type'] == 'DateTimeField':
			return 'Date'
		elif fieldDef['type'] == 'TimeField':
			return 'DateTime'
		elif fieldDef['type'] == 'CalculatedField':
			if fieldDef['display']['style'] == 'number' or fieldDef['display']['style'] == 'currency':
				return 'DecimalNumber'
			elif  fieldDef['display']['style'] == 'text':
				return 'Text'
			elif  fieldDef['display']['style'] == 'date':
				return 'Date'

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
			'label':field['label'][0:39],
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
			'label':field['label'][0:39],
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
			'label':field['label'][0:39],
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
			'label':field['label'][0:39],
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
			'label':field['label'][0:39],
			'description':field['description'],
			'valueSet':{'valueSetDefinition': {'value': self.fulcrum_process_yesno_list (field)}},
			'required':field['required']
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_classificationpicklist (self, field):
		sfdcField = {
			'type':'MultiselectPicklist',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'][0:39],
			'description':field['description'],
			'valueSet':{'restricted':False,'valueSetDefinition': {'value': [{'default':False,
				'label':'Classification Field',
				'fullName':'Classification_Field'
			}]}},
			'required':field['required'],
			'visibleLines':10
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_yesnoneutral_picklist (self, field):
		sfdcField = {
			'type':'Picklist',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'][0:39],
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
			'label':field['label'][0:39],
			'description':field['description'],
			'valueSet':{'valueSetDefinition': {'value': self.fulcrum_process_choice_list (field)}},
			'required':field['required'],
			'visibleLines':10
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_masterdetail (self, field, parentId, parentLabel, junction=False):
		fieldKey = field['key'].replace('-','_')
		fullName = _sfdcPrefix + fieldKey
		relationshipName = _sfdcPrefix + parentId[2:15].replace('-','_') + '_' + fieldKey

		if junction == False:
			sfdcField = {
				'type':'MasterDetail',
				'fullName': fullName + '_d__c',
				'label':parentLabel[0:39],
				'description':field['description'],
				'referenceTo':parentId,
				'relationshipLabel':field['label'] + 's',
				'relationshipName':relationshipName + '_d'
			}
		else:
			sfdcField = {
				'type':'MasterDetail',
				'fullName': fullName + '_d2__c',
				'label':parentLabel[0:39],
				'description':field['description'],
				'referenceTo':parentId,
				'relationshipLabel':field['label'] + 's',
				'relationshipName':relationshipName + '_d',
				'relationshipOrder':1
			}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_url (self, field):
		sfdcField = {
			'type':'Url',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'][0:39],
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
			'label':field['label'][0:39],
			'description':field['description'],
			'required':field['required'],
			'referenceTo': (_sfdcPrefix + field['form_id'] + '__c').replace('-','_'),
			'relationshipLabel':field['label'] + 's',
			'relationshipName': _sfdcPrefix + field['form_id'][0:13].replace('-','_') + '_' + field['key'] + '_d',
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_custom_field_date (self, field):
		sfdcField = {
			'type':'Date',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'][0:39],
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
			'label':timeField['label'][0:39],
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
			'label':field['label'][0:39],
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
		sfdcField.append ( self.salesforce_custom_field_text ({'key':field['key'] + '_1',
			'label':field['label'][0:30] + ' Street #',
			'required': False,
			'description': field['label'] + ' Street Number'}))

		sfdcField.append ( self.salesforce_custom_field_text ({'key':field['key'] + '_2',
			'label':field['label'][0:32] + ' Street',
			'required': False,
			'description': field['label'] + ' Street'}))

		sfdcField.append ( self.salesforce_custom_field_text ({'key':field['key'] + '_3',
			'label':field['label'][0:33] + ' Suite',
			'required': False,
			'description': field['label'] + ' Suite'}))

		sfdcField.append ( self.salesforce_custom_field_text ({'key':field['key'] + '_4',
			'label':field['label'][0:34] + ' City',
			'required': False,
			'description': field['label'] + ' City'}))

		sfdcField.append ( self.salesforce_custom_field_text ({'key':field['key'] + '_5',
			'label':field['label'][0:32] + ' County',
			'required': False,
			'description': field['label'] + ' County'}))

		sfdcField.append ( self.salesforce_custom_field_text ({'key':field['key'] + '_6',
			'label':field['label'][0:33] + ' State',
			'required': False,
			'description': field['label'] + ' State/Province'}))

		sfdcField.append ( self.salesforce_custom_field_text ({'key':field['key'] + '_7',
			'label':field['label'][0:27] + ' Postal Code',
			'required': False,
			'description': field['label'] + ' Postal Code'}))

		sfdcField.append ( self.salesforce_custom_field_text ({'key':field['key'] + '_8',
			'label':field['label'][0:31] + ' Country',
			'required': False,
			'description': field['label'] + ' Country'}))
		return sfdcField

	#Sets an External ID Field
	def salesforce_custom_field_barcode (self, field):
		sfdcField = {
			'type':'Text',
			'fullName': _sfdcPrefix + field['key'] + '__c',
			'label':field['label'][0:39],
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
			'label':field['label'][0:39],
			'description':field['description'],
			'required':field['required'],
			'scale':9
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_integration_field_fulcrum_id (self, required=True):
		sfdcField = {
			'type':'Text',
			'fullName': _sfdcPrefix + 'Fulcrum_Id__c',
			'label':'Fulcrum Id',
			'description':'Fulcrum Generated Record Id',
			'length':255,
			'required':required,
			'externalId':True,
			'unique':True
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_integration_field_project_id (self):
		sfdcField = {
			'type':'Text',
			'fullName': _sfdcPrefix + 'project_id__c',
			'label':'Fulcrum Project Id',
			'description':'Fulcrum Generated Project Id',
			'length':255,
			'required':False,
			'externalId':True
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_integration_field_assigned_to (self):
		sfdcField = {
			'type':'Text',
			'fullName': _sfdcPrefix + 'assigned_to__c',
			'label':'Assigned To',
			'description':'Record is assigned to this person in Fulcrum',
			'length':255,
			'required':False,
			'externalId':False
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_integration_field_assigned_to_id (self):
		sfdcField = {
			'type':'Text',
			'fullName': _sfdcPrefix + 'assigned_to_id__c',
			'label':"Fulcrum Assigned To Id",
			'description':'The Fulcrum User ID that this record is Assigned To',
			'length':255,
			'required':False,
			'externalId':False
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	def salesforce_integration_field_project_id_lookup (self, data):
		self.construct_sfdc_fulcrum_project_object ()
		sfdcField = {
			'type':'Lookup',
			'fullName': _sfdcPrefix + 'fulcrum_project__c',
			'label':"Fulcrum Project",
			'description':'Link to Fulcrum Project Object for reporting purposes',
			'required':False,
			'referenceTo': _sfdcPrefix + 'Fulcrum_Project__c',
			'relationshipLabel':'Fulcrum Projects',
			'relationshipName':'fp_' + data['id'].replace('-','_')
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
			'scale':9
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +')'
		return sfdcField

	# Take an array of values representing fields
	def fulcrum_map_title_field_keys_to_salesforce_fields (self, array, data):
		i = 0
		sfdcTitle = ''
		for value in array:
			objectId = _sfdcPrefix + value.replace('-','_') + '__c'
			if i == 0:
				for field in data['elements']:
					if value == field['key']:
						fieldType = self.map_fulcrum_field_to_datatype (field)
						if fieldType == 'Text' or fieldType == 'Barcode':
							sfdcTitle = objectId
						elif fieldType == 'DecimalNumber' or fieldType == 'IntegerNumber' or fieldType == 'DecimalNumber' or fieldType == 'YesNoPicklist' or fieldType == 'YesNoNeutralPicklist' or fieldType == 'Picklist':
							sfdcTitle = "TEXT("+objectId+")"
			else:
				for field in data['elements']:
					if value == field['key']:
						fieldType = self.map_fulcrum_field_to_datatype (field)
						if fieldType == 'Text' or fieldType == 'Barcode':
							sfdcTitle += ' + " | " + ' + objectId
						elif fieldType == 'DecimalNumber' or fieldType == 'IntegerNumber' or fieldType == 'DecimalNumber' or fieldType == 'YesNoPicklist' or fieldType == 'YesNoNeutralPicklist' or fieldType == 'Picklist':
							sfdcTitle += ' + " | " + ' + "TEXT("+objectId+")"
			i += 1
		return sfdcTitle


	def fulcrum_title_to_salesforce_formula (self, data):
		formula = self.fulcrum_map_title_field_keys_to_salesforce_fields (data['title_field_keys'], data)
		sfdcField = {
			'type':'Text',
			'fullName': _sfdcPrefix + 'Title__c',
			'label':'Title',
			'description':'Title as displayed in Fulcrum',
			'formula':formula
		}
		print '   Creating Field! '+ sfdcField['fullName'] + ' : ' + sfdcField['label'] +' ('+ sfdcField['type'] +') ' + formula
		return sfdcField

	# Determines the type of field, and generates the field structure of the object

	def fulcrum_to_salesforce_field_elements (self, data, elements, action='Test'):
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
				sfdcFields.extend ( self.fulcrum_to_salesforce_field_elements (data, field['elements']) )
			elif fieldType == 'Picklist':
				sfdcFields.append ( self.salesforce_custom_field_picklist (field) )
			elif fieldType == 'MultiSelectPicklist':
				sfdcFields.append ( self.salesforce_custom_field_multiselectpicklist (field) )
			elif fieldType == 'ClassificationField':
				sfdcFields.append ( self.salesforce_custom_field_classificationpicklist (field) )
			elif fieldType == 'Address':
				sfdcFields.extend ( self.salesforce_custom_field_address (field) )
			elif fieldType == 'Barcode':
				sfdcFields.append ( self.salesforce_custom_field_barcode (field) )
			elif fieldType == 'URL':
				sfdcFields.append ( self.salesforce_custom_field_url (field) )
			elif fieldType == 'Lookup':
				sfdcFields.append ( self.salesforce_custom_field_lookup (field) )
				if action != 'recurseCreate' or action != 'recurseUpdate':
					if field['form_id'] != data['id']:
						print '	  Creating Related Application'
						fulcrumForm = self.fulcrum.forms.find(field['form_id'])
						if action == 'create':
							action = 'recurseCreate'
						elif action == 'update':
							action = 'recurseUpdate'

						# Yay recursion! This doesn't work here, need a lot of checks to ensure you're not duplicating the same thing over and over.
						# Another problem, another day.  Just run this again for linked.
						# Create Salesforce Object From Fulcrum Form (and add new fields if it's created)
						print 'Creating Related Applications Related To Junction Objct!'
						print 'You must add Permissions, they will not be included in the created Permission Set'
						createResult = self.construct_fulcrum_sfdc_object (fulcrumForm['form'], action=action, permissions=False)

			elif fieldType == 'Date':
				sfdcFields.append ( self.salesforce_custom_field_date (field) )
			# Date time is special.  There is no Time field in Salesforce.
			# Instead, if we encouter this type, do a child interation of elements
			# To determine if there is a Date field directly preceeding this Date Time field
			# This mapping will duplicate dates Twice if a Time is specificed directly below
			# This is a desired functionality trait (not a bug seriously I thought about this)
			elif fieldType == 'DateTime':
				j = 0
				isDateFieldDetected = False
				for iterateForDateField in elements:
					isDateFieldType = self.map_fulcrum_field_to_datatype (iterateForDateField)
					if isDateFieldType == 'Date':
						isDateFieldDetected = True
						# Check to see that the Date field exists before this Time field to pair them
						if i-j == 1:
							isDateFieldDetected = True
							sfdcFields.append ( self.salesforce_custom_field_datetime (iterateForDateField, field) )
					j += 1
				sfdcFields.append ( self.salesforce_custom_field_text (field) )
			#Do nothing.
			#elif fieldType == 'Photo' or fieldType == 'Video' or fieldType == 'Audio' or fieldType == 'Signature' or fieldType == 'MasterDetail':
				#sfdcFields.append ( self.salesforce_custom_field_longtextarea (field) )

			i += 1

		return sfdcFields

	def fulcrum_process_junction_object (self, data, field, parentId, parentLabel, action):
		sfdcFields = []

		childId = _sfdcPrefix + field['form_id'].replace('-','_') + '__c'

		sfdcFields.append ( self.salesforce_custom_field_masterdetail (field, parentId, parentLabel))
		sfdcFields.append ( self.salesforce_custom_field_masterdetail (field, childId, field['label'], junction=True))
		sfdcFields.append ( self.salesforce_integration_field_fulcrum_id ())

		#Ensure Linked Object Is Created / Updated
		# Get Individual Fulcrum Form Fulcrum Applications
		fulcrumForm = self.fulcrum.forms.find(field['form_id'])

		# Yay recursion!
		# Create Salesforce Object From Fulcrum Form (and add new fields if it's created)
		print 'Creating Related Applications Related To Junction Objct!'
		print 'You must add Permissions, they will not be included in the created Permission Set'
		createResult = self.construct_fulcrum_sfdc_object (fulcrumForm['form'], action=action, permissions=False	)
		#figure out what to do with this recursive result.

		return sfdcFields

	def fulcrum_multiple_lookup_as_sfdc_junction_object (self, data, parentId, parentLabel, action, permissions=True):
		for field in data['elements']:
			fieldType = self.map_fulcrum_field_to_datatype (field)
			if fieldType == 'Junction':
				#Create New Object with a Master Detail Relationship
				return self.construct_fulcrum_sfdc_object_junction (data, field, parentId, parentLabel, action=action, permissions=permissions)

	def construct_fulcrum_sfdc_object_junction (self, data, field, parentId, parentLabel, action, permissions=True):
		print 'Creating Junction Object!'
		print 'Label: ' + field['label']
		#Appends the first 13 characters of the Form ID to the Key to prevent collissions
		junctionFullName = _sfdcPrefix + data['id'][0:13].replace('-','_') + '_' + field['key'].replace('-','_') + '_j__c'
		print 'FullName: ' + junctionFullName
		xml = ''

		sfdcObject = {'label':field['label'][0:39],
				'pluralLabel':field['label'][0:38] + 's',
				'fullName': junctionFullName,
				'sharingModel':'ControlledByParent',
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
					'displayFormat':_sfdcAutoNumberDisplayMaster},
				}

		xml += dicttoxml.dicttoxml(sfdcObject, item_func=_item_to_none_func, attr_type=False, root=False).replace('<value>','').replace('</value>','').replace('<None>','').replace('</None>','')

		sfdcFields = self.fulcrum_process_junction_object (data, field, parentId, parentLabel, action)

		for sfdcField in sfdcFields:
			xml += dicttoxml.dicttoxml({'fields': sfdcField}, item_func=_item_to_none_func, attr_type=False, root=False).replace('<value>','').replace('</value>','').replace('<None>','').replace('</None>','')

		action = self.commit_salesforce_change (xml, action=action)

		#if permissions == True and sfdcFields is not None:
		#	print 'SFDC FIELDS--------BEGIN'
		#	print sfdcFields
		#	print 'SFDC FIELDS--------END'
		#	permissionResult = self.construct_sfdc_object_permissions (sfdcObject, sfdcFields, action)
		#	return [action, permissionResult] 
		#else:
		#	return action

		return action

	#Generates all of the repeatable sections on the object as details
	def fulcrum_repeatable_sections_as_sfdc_master_detail (self, data, parentId, parentLabel, action=True, permissions=True):
		for field in data['elements']:
			fieldType = self.map_fulcrum_field_to_datatype (field)
			if fieldType == 'MasterDetail':
				#Create New Object with a Master Detail Relationship
				self.construct_fulcrum_sfdc_object_child (field, parentId, parentLabel, action=action, permissions=permissions)

	def commit_salesforce_change (self, xml, action='Test', metadataType='CustomObject'):
		if action == 'create' or action == 'recurseCreate':
			result = self.sfdc.createMetadata (xml, metadataType)
			return result
		elif action == 'update' or action == 'recurseUpdate':
			result = self.sfdc.updateMetadata (xml, metadataType)
			return result
		else:
			print '...TESTING... Use action create or update to commit. ...TESTING...'
			print xml
			print '...TESTING... Use action create or update to commit. ...TESTING...'

	def create_application_tab_in_salesforce (self, data, action='Test'):
		sfdcCustomTabObject = {
			'description': data['description'],
			'fullName':_sfdcPrefix + data['id'].replace('-','_') + '__c',
			'mobileReady': True,
			'motif':'Custom68:Globe',
			'customObject': True
		}

		self.sfdcPermissionSetTabSettings = {'tab':sfdcCustomTabObject['fullName'],
			'visibility':'Visible'}

		xml = dicttoxml.dicttoxml (sfdcCustomTabObject, attr_type=False, root=False)

		result = self.sfdc.createMetadata (xml, 'CustomTab')

		return result


	def commit_sfdc_permissions_set_change (self, xml, action='Test'):
		if action == 'create' or action == 'recurseCreate':
			result = self.sfdc.createMetadata (xml, 'PermissionSet')
			return result
		elif action == 'update' or action == 'recurseUpdate':
			result = self.sfdc.updateMetadata (xml, 'PermissionSet')
			return result
		else:
			print '...TESTING... Use action create or update to commit. ...TESTING...'
			print xml
			print '...TESTING... Use action create or update to commit. ...TESTING...'

	def construct_sfdc_object_permissions (self, data, fields, action='create'):
		objectPerm = {'objectPermissions' :{
			'allowCreate': True,
			'allowDelete': True,
			'allowEdit': True,
			'allowRead': True,
			'object': _sfdcPrefix + 'Fulcrum_Project__c'
			}
		}

		self.sfdcPermissionSetObjectPermissions.append (objectPerm)

		objectPerm = {'objectPermissions' :{
			'allowCreate': True,
			'allowDelete': True,
			'allowEdit': True,
			'allowRead': True,
			'object': data['fullName']
			}
		}

		self.sfdcPermissionSetObjectPermissions.append (objectPerm)

		self.sfdcPermissionSetFieldPermissions.append ({'fieldPermissions':{
								'editable':True,
								'field': _sfdcPrefix + 'Fulcrum_Project__c.Fulcrum_Id__c',
								'readable': True
							}})
		self.sfdcPermissionSetFieldPermissions.append ({'fieldPermissions':{
								'editable':True,
								'field': _sfdcPrefix + 'Fulcrum_Project__c.Name',
								'readable': True
							}})
		self.sfdcPermissionSetFieldPermissions.append ({'fieldPermissions':{
								'editable':True,
								'field': _sfdcPrefix + 'Fulcrum_Project__c.Description',
								'readable': True
							}})

		for field in fields:
			fieldPerm = {}
			if self.checkKey (field, 'type') and self.checkKey (field, 'fullName') and self.checkKey (data, 'fullName'):
				if field['fullName'] != _sfdcPrefix + 'Fulcrum_Id__c':
					required = self.checkKey (field, 'required')
					if required == True:
						required = field['required']
					if required == False:
						if field['fullName'] == _sfdcPrefix + 'Title__c':
							fieldPerm = {'fieldPermissions':{
								'editable':False,
								'field': data['fullName'] + '.' + field['fullName'],
								'readable': True
							}}
							self.sfdcPermissionSetFieldPermissions.append (fieldPerm)
						elif field['type'] != 'MasterDetail':
							fieldPerm = {'fieldPermissions':{
								'editable': True,
								'field': data['fullName'] + '.' + field['fullName'],
								'readable': True
							}}
							self.sfdcPermissionSetFieldPermissions.append (fieldPerm)

		return

	def generate_permission_set_and_send_to_salesforce (self, data, action='Test'):
		if action == 'create' or action == 'recurseCreate' and self.sfdcPermissionSetTabCreated == False:
			self.sfdcPermissionSetTabCreated = self.create_application_tab_in_salesforce (data, action='create')
			sfdcPermissionSet = {
				'label':data['name'],
				'fullName':_sfdcPrefix + data['id'].replace('-','_'),
				'description':data['description'],
				'fieldPermissionsRemoveTag': self.sfdcPermissionSetFieldPermissions,
				'objectPermissionsRemoveTag': self.sfdcPermissionSetObjectPermissions,
				'tabSettings':{'tab':_sfdcPrefix + data['id'].replace('-','_') + '__c', 'visibility':'Visible'}
			}
		else:
			sfdcPermissionSet = {
			'label':data['name'],
			'fullName':_sfdcPrefix + data['id'].replace('-','_'),
			'description':data['description'],
			'fieldPermissionsRemoveTag': self.sfdcPermissionSetFieldPermissions,
			'objectPermissionsRemoveTag': self.sfdcPermissionSetObjectPermissions,
		}

		xml = dicttoxml.dicttoxml (sfdcPermissionSet, attr_type=False, root=False).replace('<item>','').replace('</item>','').replace('<fieldPermissionsRemoveTag>','').replace('</fieldPermissionsRemoveTag>','').replace('<objectPermissionsRemoveTag>','').replace('</objectPermissionsRemoveTag>','')

		#print 'PERMISSIONS XML'
		#print xml

		result = self.commit_sfdc_permissions_set_change (xml, action)

		#print result
		#print 'END PERMISSIONS'

		return [self.sfdcPermissionSetTabCreated, result]

	# Construct Master Object
	def construct_fulcrum_sfdc_object (self, data, action='create', autonumber=True, permissions=True):
		print 'Creating Object!'
		print 'Label: ' + data['name']
		print 'FullName: ' + _sfdcPrefix + data['id'].replace('-','_') + '__c'
		sfdcFields = [
			self.salesforce_integration_field_fulcrum_id (),
			self.salesforce_integration_field_location (data),
			self.salesforce_integration_field_assigned_to (),
			self.salesforce_integration_field_assigned_to_id (),
			self.salesforce_integration_field_project_id (),
			self.salesforce_integration_field_project_id_lookup (data),
			self.fulcrum_title_to_salesforce_formula (data), #Disabled until I get titles working right
			self.salesforce_custom_field_integer_number ({'key':'created_duration', 'label':'Created Duration', 'description':'Time to initially create this record in sections','required':False}),
			self.salesforce_custom_field_integer_number ({'key':'updated_duration', 'label':'Updated Duration', 'description':'Time spent updating this updating','required':False}),
			self.salesforce_custom_field_integer_number ({'key':'edited_duration', 'label':'Edited Duration', 'description':'Time spent editing this record','required':False}),
			self.salesforce_custom_field_decimal_number ({'key':'altitude', 'label':'Altitude', 'description':'','required':False}),
			self.salesforce_custom_field_decimal_number ({'key':'speed', 'label':'Speed', 'description':'','required':False}),
			self.salesforce_custom_field_decimal_number ({'key':'course', 'label':'Course', 'description':'','required':False}),
			self.salesforce_custom_field_decimal_number ({'key':'horizontal_accuracy', 'label':'Horizontal Accuracy', 'description':'','required':False}),
			self.salesforce_custom_field_decimal_number ({'key':'vertical_accuracy', 'label':'Vertical Accuracy', 'description':'','required':False}),
			self.salesforce_custom_field_integer_number ({'key':'version', 'label':'Record Version', 'description':'Fulcrum Record Version','required':False}),
			self.salesforce_custom_field_datetime ({'key':'created', 'label':'Fulcrum Server Created Date', 'description':'Created Date Time that the Fulcrum Record was saved to the Fulcrum Server','required':False},{'key':'at', 'label':'Fulcrum Server Created Date', 'description':'Created Date Time that the Fulcrum Record was saved to the Fulcrum Server','required':False}),
			self.salesforce_custom_field_datetime ({'key':'updated', 'label':'Fulcrum Server Updated Date', 'description':'Last Updated Date Time that the Fulcrum Record was saved to Fulcrum','required':False},{'key':'at', 'label':'Fulcrum Server Updated Date', 'description':'Created Date Time that the Fulcrum Record was saved to the Fulcrum Server','required':False}),
			self.salesforce_custom_field_datetime ({'key':'client_created', 'label':'Fulcrum Client Created Date', 'description':'Created Date Time that the Fulcrum Record was Created on the Client Device','required':False},{'key':'at', 'label':'Fulcrum Client Created Date', 'description':'Created Date Time that the Fulcrum Record was saved to the Fulcrum Server','required':False}),
			self.salesforce_custom_field_datetime ({'key':'client_updated', 'label':'Fulcrum Client Updated Date', 'description':'Created Date Time that the Fulcrum Record was Updated on the Client Device','required':False},{'key':'at', 'label':'Fulcrum Client Updated Date', 'description':'Created Date Time that the Fulcrum Record was saved to the Fulcrum Server','required':False}),
			self.salesforce_custom_field_text ({'key':'created_by', 'label':'Fulcrum Created By', 'description':'The user that created this record in Fulcrum','required':False}),
			self.salesforce_custom_field_text ({'key':'created_by_id', 'label':'Fulcrum Created By Id', 'description':'The user that created this record in Fulcrum','required':False}),
			self.salesforce_custom_field_text ({'key':'updated_by', 'label':'Fulcrum Updated By', 'description':'The user that last updated this record in Fulcrum','required':False}),
			self.salesforce_custom_field_text ({'key':'updated_by_id', 'label':'Fulcrum Updated By Id', 'description':'The user that last updated this record in Fulcrum','required':False}),
			self.salesforce_custom_field_geolocation ({'key':'created_location', 'label':'Created Location', 'description':'The location that this record was created','required':False}),
			self.salesforce_custom_field_geolocation ({'key':'updated_location', 'label':'Updated Location', 'description':'The location that this record was updated','required':False}),
			self.salesforce_custom_field_text ({'key':'changeset_id', 'label':'Fulcrum Changeset Id', 'description':'','required':False}),
			self.salesforce_custom_field_text ({'key':'form_id', 'label':'Fulcrum Form Id', 'description':'Fulcrum Form Id','required':False}),
		]

		xml = ''

		if 'status_field' in data.keys():
			if data['status_field']['enabled'] == True:
				sfdcFields.append (self.salesforce_integration_field_status (data['status_field']))

		sfdcFields.extend(self.fulcrum_to_salesforce_field_elements (data, data['elements'], action=action))

		if autonumber == True:
			sfdcObject = {'label':data['name'][0:39],
				'pluralLabel':data['name'][0:38] + 's',
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
			sfdcObject = {'label':data['name'][0:39],
				'pluralLabel':data['name'][0:38] + 's',
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
		for sfdcField in sfdcFields:
			xml += dicttoxml.dicttoxml({'fields': sfdcField}, item_func=_item_to_none_func, attr_type=False, root=False).replace('<value>','').replace('</value>','').replace('<None>','<value>').replace('</None>','</value>')

		actionResult = []
		actionResult.append (self.commit_salesforce_change (xml, action))

		parentId = _sfdcPrefix + data['id'].replace('-','_') + '__c'
		parentLabel = data['name']
		repeatableSectionsResult = self.fulcrum_repeatable_sections_as_sfdc_master_detail (data, parentId, parentLabel, action=action, permissions=permissions)
		actionResult.append (repeatableSectionsResult)

		junctionObjectsResult = self.fulcrum_multiple_lookup_as_sfdc_junction_object (data, parentId, parentLabel, action=action, permissions=permissions)
		actionResult.append (junctionObjectsResult)

		if permissions == True:
			actionResult.append (self.construct_sfdc_object_permissions (sfdcObject, sfdcFields, action))
			permissionsSetResult = self.generate_permission_set_and_send_to_salesforce (data, action)
			actionResult.append (permissionsSetResult)

		return actionResult

	## Constructs Detail Objects
	def construct_fulcrum_sfdc_object_child (self, data, parentId, parentLabel, action = 'create', permissions=True):
		print 'Creating ' + parentLabel + ' Detail Object! '
		print 'Label: ' + data['label']
		fullName = _sfdcPrefix + parentId[2:15] + '_' + data['key'].replace('-', '_')

		sfdcObject = {'label':data['label'][0:39],
			'pluralLabel':data['label'][0:38] + 's',
			'fullName': fullName + '_d' + '__c',
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

		print "FullName: " + sfdcObject['fullName']

		sfdcFields = [
			self.salesforce_integration_field_fulcrum_id (),
			self.salesforce_integration_field_location (data),
			self.fulcrum_title_to_salesforce_formula (data), #Disabled until I get titles working right
			self.salesforce_custom_field_masterdetail (data, parentId, parentLabel),
			self.salesforce_custom_field_text ({'key':'created_by_id', 'label':'Fulcrum Created By Id', 'description':'The user that created this record in Fulcrum','required':False}),
			self.salesforce_custom_field_text ({'key':'updated_by_id', 'label':'Fulcrum Last Updated By Id', 'description':'The user that last updated this record in Fulcrum','required':False}),
			self.salesforce_custom_field_integer_number ({'key':'created_duration', 'label':'Created Duration', 'description':'Time to initially create this record in sections','required':False}),
			self.salesforce_custom_field_integer_number ({'key':'updated_duration', 'label':'Updated Duration', 'description':'Time spent updating this updating','required':False}),
			self.salesforce_custom_field_integer_number ({'key':'edited_duration', 'label':'Edited Duration', 'description':'Time spent editing this record','required':False}),
			self.salesforce_custom_field_integer_number ({'key':'version', 'label':'Record Version', 'description':'Fulcrum Record Version','required':False}),
			self.salesforce_custom_field_text ({'key':'changeset_id', 'label':'Fulcrum Changeset Id', 'description':'','required':False}),
			self.salesforce_custom_field_datetime ({'key':'created', 'label':'Fulcrum Server Created Date', 'description':'Created Date Time that the Fulcrum Record was saved to the Fulcrum Server','required':False},{'key':'at', 'label':'Fulcrum Server Created At', 'description':'Created Date Time that the Fulcrum Record was saved to the Fulcrum Server','required':False}),
			self.salesforce_custom_field_datetime ({'key':'updated', 'label':'Fulcrum Server Updated Date', 'description':'Last Updated Date Time that the Fulcrum Record was saved to Fulcrum','required':False},{'key':'at', 'label':'Fulcrum Server Updated At', 'description':'Last Updated Date Time that the Fulcrum Record was saved to Fulcrum','required':False}),
			self.salesforce_custom_field_text ({'key':'form_id', 'label':'Fulcrum Form Id', 'description':'Fulcrum Form Id','required':False}),
		]

		xml = ''

		# Leave the .replace on here.  It's to get rid of a duplicate parent Item keys for nested tables
		xml += dicttoxml.dicttoxml(sfdcObject, item_func=_item_to_none_func, attr_type=False, root=False).replace('<value>','').replace('</value>','').replace('<None>','<value>').replace('</None>','</value>')

		sfdcFields.extend (self.fulcrum_to_salesforce_field_elements (data, data['elements']))

		for sfdcField in sfdcFields:
			# Leave the .replace on here.  It's to get rid of a duplicate parent Item keys for nested tables
			xml += dicttoxml.dicttoxml({'fields': sfdcField}, item_func=_item_to_none_func, attr_type=False, root=False).replace('<value>','').replace('</value>','').replace('<None>','<value>').replace('</None>','</value>')

		actionResult = []

		actionResult.append (self.commit_salesforce_change (xml, action))

		junctionObjectsResult = self.fulcrum_multiple_lookup_as_sfdc_junction_object (data, parentId, parentLabel, action)
		actionResult.append(junctionObjectsResult)

		if permissions == True:
			actionResult.append (self.construct_sfdc_object_permissions (sfdcObject, sfdcFields, action))

		return actionResult

	def construct_sfdc_fulcrum_project_object (self, action='create'):
		print 'Creating Fulcrum Project Object!'
		xml = ''

		sfdcObject = {'label':'Fulcrum Project',
			'pluralLabel':'Fulcum Projects',
			'fullName': _sfdcPrefix + 'fulcrum_project__c',
			'sharingModel':'ReadWrite',
			'deploymentStatus':'Deployed',
			'startsWith':self.startsWithVowel('Fulcrum Project'),
			'description':'Projects are tags that you can tag your records with. Once a record is tagged with a project only users that have been granted access to that project will be able to see and edit the records tagged with that project. http://help.fulcrumapp.com/web-app/homepage/what-are-projects',
			'enableActivities':True,
			'enableHistory':True,
			'enableReports':True,
			'enableSearch':True,
			'nameField':{'type':'Text',
				'label':'Fulcrum Project Name'
			}
		}

		xml += dicttoxml.dicttoxml(sfdcObject, item_func=_item_to_none_func, attr_type=False, root=False).replace('<value>','').replace('</value>','').replace('<None>','<value>').replace('</None>','</value>')

		sfdcFields = [
			self.salesforce_integration_field_fulcrum_id (),
			self.salesforce_custom_field_text ({'key':'description', 'label':'Description', 'description':'Description of this project from Fulcrum','required':False}),
			self.salesforce_custom_field_datetime ({'key':'created', 'label':'Fulcrum Server Created Date', 'description':'Created Date Time that the Fulcrum Record was saved to the Fulcrum Server','required':False},{'key':'at', 'label':'Fulcrum Server Created Date', 'description':'Created Date Time that the Fulcrum Record was saved to the Fulcrum Server','required':False}),
			self.salesforce_custom_field_datetime ({'key':'updated', 'label':'Fulcrum Server Updated Date', 'description':'Last Updated Date Time that the Fulcrum Record was saved to Fulcrum','required':False},{'key':'at', 'label':'Fulcrum Server Created Date', 'description':'Created Date Time that the Fulcrum Record was saved to the Fulcrum Server','required':False}),
		]

		for sfdcField in sfdcFields:
			xml += dicttoxml.dicttoxml({'fields': sfdcField}, item_func=_item_to_none_func, attr_type=False, root=False).replace('<value>','').replace('</value>','').replace('<None>','<value>').replace('</None>','</value>')

		return self.commit_salesforce_change (xml, action)

	# Creates a fulcrum_id field on the ContentVersion Object
	def provision_sfdc_content_version_object (self, action='create'):
		print 'Provisioning Salesforce ContentVersion Object!'
		xml = ''

		sfdcObject = {
			'fullName': 'ContentVersion'
		}

		xml += dicttoxml.dicttoxml(sfdcObject, item_func=_item_to_none_func, attr_type=False, root=False).replace('<value>','').replace('</value>','').replace('<None>','<value>').replace('</None>','</value>')

		sfdcFields = [
			self.salesforce_integration_field_fulcrum_id (required=False),
			self.salesforce_integration_field_location ({'key':'location', 'label':'Location', 'description':'Geolocation of this file','geometry_required':False}),
		]

		for sfdcField in sfdcFields:
			xml += dicttoxml.dicttoxml({'fields': sfdcField}, item_func=_item_to_none_func, attr_type=False, root=False).replace('<value>','').replace('</value>','').replace('<None>','<value>').replace('</None>','</value>')

		print xml

		return self.commit_salesforce_change (xml, action)
