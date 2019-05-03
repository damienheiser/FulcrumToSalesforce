import json
import SalesforceMetadataModule as smm
import dicttoxml
from xml.dom.minidom import parseString
from fulcrum import Fulcrum
import re
import collections
import time
import datetime
import requests
import base64
import string
import random

from simple_salesforce import Salesforce
from simple_salesforce import SalesforceLogin
from simple_salesforce import SFType

_sfdcPrefix = 'f_'
_sfdcUsername = ""
_sfdcPassword = ""
_sfdcToken = ""
_sfdcDomain = 'test'

# Set _sfdcSandbox to False to run in production
_sfdcSandbox = True
_isDateFieldDefault = False

_fulcrumXApiToken = ""
_fulcrumBaseURL = 'https://api.fulcrumapp.com/api/v2/'

class FulcrumRecordToSalesforceRecord:

	_sfdcSession_id, _sfdcInstance = SalesforceLogin(username=_sfdcUsername, password=_sfdcPassword, security_token=_sfdcToken, domain=_sfdcDomain)
	sfdc = Salesforce(instance=_sfdcInstance, session_id=_sfdcSession_id)
	fulcrum = Fulcrum(key=_fulcrumXApiToken)
	fulcrumHeaders = {'X-ApiToken': _fulcrumXApiToken}

	def sf_api_call(self, action, parameters = {}, method = 'get', data = {}, multipart=False, boundary=None):
		"""
		Helper function to make calls to Salesforce REST API.
		Parameters: action (the URL), URL params, method (get, post or patch), data for POST/PATCH.
		"""
		headers = {}
		if multipart == False:
			headers = {
				'Content-type': 'application/json',
				'Accept-Encoding': 'gzip',
				'Authorization': 'OAuth ' + self._sfdcSession_id,
			}
		else:
			headers = {
				'Content-type': 'multipart/form-data; boundary='+boundary,
				'Accept-Encoding': 'gzip',
				'Authorization': 'OAuth ' + self._sfdcSession_id,
			}
		if method == 'get':
			r = requests.request(method, 'https://'+self._sfdcInstance+action, headers=headers, params=parameters, timeout=30)
		elif method in ['post', 'patch']:
			r = requests.request(method, 'https://'+self._sfdcInstance+action, headers=headers, json=data, params=parameters, timeout=10)
		else:
			# other methods not implemented in this example
			raise ValueError('Method should be get or post or patch.')
		#print('Debug: API %s call: %s' % (method, r.url) )
		if r.status_code < 300:
			if method=='patch':
				return None
			else:
				return r.json()
		else:
			raise Exception('API error when calling %s : %s' % (r.url, r.content))

	# Generates a random string
	def id_generator(self, size=32, chars=string.ascii_uppercase + string.digits):
		return ''.join(random.choice(chars) for _ in range(size))

	#checks to see if a key exists in a dictonary
	def checkKey (self, dictionary, key):
		try:
			if key in dictionary.keys(): 
				return True
			else:
				return False
		except KeyError:
			return False

	## pass JSON Directly
	def composite_salesforce_create (self, objectId, records):
		response = self.sfdc.restful (method='POST', path='composite/tree/'+objectId, json=records)
		return response

	#must have Salesforce record IDs
	def composite_salesforce_update (self, objectId, extCustomField, extIdValue, records):
		response = self.sfdc.restful (method='PATCH', path='composite/sobjects', json=records)
		return response

	def composite_salesforce_request (self, objectId, extCustomField, extIdValue, records):
		response = self.sfdc.restful (method='POST', path='composite/sobjects/' + objectId, json=records)
		return reponse

	# Data should either be a single JSON encapsulating base64 encoded blob up to 34MB
	# Or a multipart message encapsulating a base64 encoded blob up to 2GB
	# https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/dome_sobject_insert_update_blob.htm
	def contentVersion_salesforce_create (self, data):
		return self.sf_api_call('/services/data/v40.0/sobjects/ContentVersion', method="post", data=data)

	def contentVersion_2GB_salesforce_create (self, data, boundary):
		return self.sf_api_call('/services/data/v40.0/sobjects/ContentVersion', method="post", data=data, multipart=True, boundary=boundary)

	# Data should be an ID
	def contentVersion_salesforce_get (self, data):
		return self.sf_api_call('/services/data/v40.0/sobjects/ContentVersion/%s' % data)


	def contentDocumentLink_salesforce_create (self, data):
		return self.sf_api_call('/services/data/v40.0/sobjects/ContentDocumentLink', method = 'post', data=data)

	def create_output_json (self, recordJson):
		recordJson = json.dumps (recordJson)
		recordJson = recordJson[1:-1]
		recordJson = recordJson.replace('null', '')
		return recordJson

	def process_generate_field (self, fieldId, fieldValue, fieldType='Data'):
		print '   ' + str(fieldType) + ': ' + str(_sfdcPrefix) + str(fieldId) + '__c:' + str(fieldValue)
		if fieldType == 'Latitude' or fieldType == 'Longitude':
			return {_sfdcPrefix + fieldId + '__' + fieldType +'__s' : fieldValue}
		else:
			return {_sfdcPrefix + fieldId + '__c' : fieldValue}

	def upload_2GB_file_to_salesforce_and_attach_to_record (self, recordId, fileTitle, fileDescription, fileName, fileContents):
		boundary = self.id_generator ()

		fileContents = base64.b64encode(fileContents)

		#Multi part request can handle 2GB Max
		ContentVersionMetadata = {
			'Title':fileTitle,
			'Description':fileDescription,
			'PathOnClient':fileName,
		}

		ContentVersionData = """--"""+boundary+"""
Content-Disposition: form-data; name="entity_content";
Content-Type: application/json

{
	"Title" : """+'"'+fileTitle+'"'+""",
	"Description" : """+'"'+fileDescription+'"'+""",
	"PathOnClient" : """+'"'+fileName+'"'+"""
}

--"""+boundary+"""
Content-Disposition: form-data; name="VersionData"; filename=""" + '"' + fileName + '"' +"""
Content-Type: application/octet-stream

""" + fileContents + """

--"""+boundary+"""--"""

		# 1: Insert the Content Document
		ContentVersion = self.contentVersion_2GB_salesforce_create (data=ContentVersionData, boundary=boundary)
		ContentVersionId = ContentVersion.get('id')

		# 2: Get the ContentDocumentId from the just inserted ContentVersion
		ContentVersion = self.contentVersion_salesforce_get (ContentVersionId)
		ContentDocumentId = ContentVersion.get('ContentDocumentId')

		# 3: Create a ContentDocumentLink between the ContentDocumentId and the Record
		contentDocumentLinkMetadata = {
			'ContentDocumentId': ContentDocumentId,
			'LinkedEntityId': recordId,
				'ShareType': 'V'
			}

		ContentDocumentLink = self.contentDocumentLink_salesforce_create (contentDocumentLinkMetadata)
		return {'ContentVersionId' : ContentVersionId, 'ContentDocumentId' : ContentDocumentId, 'ContentDocumentLink' : ContentDocumentLink}


	def upload_file_to_salesforce_and_attach_to_record (self, recordId, fileTitle, fileDescription, fileName, fileContent, fulcrumId):
		fileContent = base64.b64encode(fileContent)

		#Single part request can handle ~34MB Max
		ContentVersionData = {
			'Title':fileTitle,
			'Description':fileDescription,
			'PathOnClient':fileName,
			'VersionData':fileContent,
			_sfdcPrefix + 'Fulcrum_Id__c':fulcrumId,
		#	_sfdcPrefix + 'Location__c':fulcrumLocation
		}

		# 1: Insert the Content Document
		ContentVersion = self.contentVersion_salesforce_create (data=ContentVersionData)
		ContentVersionId = ContentVersion.get('id')

		# 2: Get the ContentDocumentId from the just inserted ContentVersion
		ContentVersion = self.contentVersion_salesforce_get (ContentVersionId)
		ContentDocumentId = ContentVersion.get('ContentDocumentId')

		# 3: Create a ContentDocumentLink between the ContentDocumentId and the Record
		contentDocumentLinkMetadata = {
			'ContentDocumentId': ContentDocumentId,
			'LinkedEntityId': recordId,
				'ShareType': 'V'
			}

		ContentDocumentLink = self.contentDocumentLink_salesforce_create (contentDocumentLinkMetadata)
		return {'ContentVersionId' : ContentVersionId, 'ContentDocumentId' : ContentDocumentId, 'ContentDocumentLink' : ContentDocumentLink}

	def process_file_fields (self, record, recordId):
		#print record
		newFiles = []
		for fieldId in record['form_values']:
			files = self.detect_file_field_type_and_process_field (fieldId, record, recordId=recordId)
			#print files
			if isinstance (files, dict):
				newFiles.append (files)

		return newFiles

	def process_video_field (self, fieldValue, recordId):
		print 'Downloading Video File From Fulcrum ... ' + fieldValue['video_id']
		baseurl = _fulcrumBaseURL + 'videos/' + fieldValue['video_id']
		blob = requests.request ('GET', baseurl + '.mp4', headers=self.fulcrumHeaders)
		if blob.status_code == 200:
			videoMetadata = self.fulcrum.videos.find(fieldValue['video_id'])
			print 'Uploading Video File To Salesforce... ' + recordId
			self.upload_file_to_salesforce_and_attach_to_record (recordId=recordId, fileTitle=fieldValue['video_id'] + ' Video', fileDescription=fieldValue['caption'], fileName=fieldValue['video_id'] + '.mp4', fileContent=blob.content, fulcrumId=fieldValue['video_id'])

		blob = requests.request ('GET', baseurl + '/track.json', headers=self.fulcrumHeaders)
		if blob.status_code == 200:
			print 'Uploading Video Track To Salesforce... ' + recordId
			self.upload_file_to_salesforce_and_attach_to_record (recordId=recordId, fileTitle=fieldValue['video_id'] + ' JSON Track', fileDescription='JSON Track Of\n' + fieldValue['caption'], fileName=fieldValue['video_id'] + '-track.json', fileContent=blob.content)

		blob = requests.request ('GET', baseurl + '/track.geojson', headers=self.fulcrumHeaders)
		if blob.status_code == 200:
			print 'Uploading Video GeoJSON Track To Salesforce... ' + recordId
			self.upload_file_to_salesforce_and_attach_to_record (recordId=recordId, fileTitle=fieldValue['video_id'] + ' GEO JSON Track', fileDescription='GeoJSON Track Of\n' + fieldValue['caption'], fileName=fieldValue['video_id'] + '-track.geojson', fileContent=blob.content)

		blob = requests.request ('GET', baseurl + '/track.gpx', headers=self.fulcrumHeaders)
		if blob.status_code == 200:
			print 'Uploading Video GPX Track To Salesforce... ' + recordId
			self.upload_file_to_salesforce_and_attach_to_record (recordId=recordId, fileTitle=fieldValue['video_id'] + ' GPX Track', fileDescription='GPX Track Track Of\n' + fieldValue['caption'], fileName=fieldValue['video_id'] + '-track.gpx', fileContent=blob.content)

		blob = requests.request ('GET', baseurl + '/track.kml', headers=self.fulcrumHeaders)
		if blob.status_code == 200:
			print 'Uploading Video KML Track To Salesforce... ' + recordId
			self.upload_file_to_salesforce_and_attach_to_record (recordId=recordId, fileTitle=fieldValue['video_id'] + ' KML Track', fileDescription='KML Track Track Of\n' + fieldValue['caption'], fileName=fieldValue['video_id'] + '-track.kml', fileContent=blob.content)

		return

	def process_photo_field (self, fieldValue, recordId):
		print 'Downloading Photo File From Fulcrum ... ' + fieldValue['photo_id']
		blob = requests.request ('GET', _fulcrumBaseURL + 'photos/' + fieldValue['photo_id'] + '.jpg', headers=self.fulcrumHeaders)
		if blob.status_code == 200:
			print 'Uploading Photo File To Salesforce... ' + recordId
			self.upload_file_to_salesforce_and_attach_to_record (recordId=recordId, fileTitle=fieldValue['photo_id'] + ' Photo', fileDescription=fieldValue['caption'], fileName=fieldValue['photo_id'] + '.jpg', fileContent=blob.content, fulcrumId=fieldValue['photo_id'])
		return

	def process_signature_field (self, fieldValue, recordId):
		print 'Downloading Signature File From Fulcrum ... ' + fieldValue['signature_id']
		blob = requests.request ('GET', _fulcrumBaseURL + 'signature/' + fieldValue['signature_id'] + '.png', headers=self.fulcrumHeaders)
		if blob.status_code == 200:
			print 'Uploading Signature File To Salesforce... ' + recordId
			self.upload_file_to_salesforce_and_attach_to_record (recordId=recordId, fileTitle=fieldValue['photo_id'] + ' Signature', fileDescription='Signed At: ' + fieldValue['timestamp'], fileName=fieldValue['signature_id'] + '.png', fileContent=blob.content, fulcrumId=fieldValue['signature_id'])
		return

	def process_audio_field (self, fieldValue, recordId):
		print 'Downloading Audio File From Fulcrum ... ' + fieldValue['audio_id']
		blob = requests.request ('GET', _fulcrumBaseURL + 'audio/' + fieldValue['audio_id'] + '.mp4', headers=self.fulcrumHeaders)
		if blob.status_code == 200:
			print 'Uploading Audio File To Salesforce... ' + recordId
			self.upload_file_to_salesforce_and_attach_to_record (recordId=recordId, fileTitle=fieldValue['audio_id'] + ' Video', fileDescription=fieldValue['caption'], fileName=fieldValue['audio_id'] + '.mp4', fileContent=blob.content, fulcrumId=fieldValue['audio_id'])

		blob = requests.request ('GET', _fulcrumBaseURL + 'audio/' + fieldValue['audio_id'] + '/track.json', headers=self.fulcrumHeaders)
		if blob.status_code == 200:
			print 'Uploading Audio Track To Salesforce... ' + recordId
			self.upload_file_to_salesforce_and_attach_to_record (recordId=recordId, fileTitle=fieldValue['audio_id'] + ' JSON Track', fileDescription='JSON Track Of\n' + fieldValue['caption'], fileName=fieldValue['audio_id'] + '-track.json', fileContent=blob.content)

		blob = requests.request ('GET', _fulcrumBaseURL + 'audio/' + fieldValue['audio_id'] + '/track.geojson', headers=self.fulcrumHeaders)
		if blob.status_code == 200:
			print 'Uploading Audio GeoJSON Track To Salesforce... ' + recordId
			self.upload_file_to_salesforce_and_attach_to_record (recordId=recordId, fileTitle=fieldValue['audio_id'] + ' GEO JSON Track', fileDescription='GeoJSON Track Of\n' + fieldValue['caption'], fileName=fieldValue['audio_id'] + '-track.geojson', fileContent=blob.content)

		blob = requests.request ('GET', _fulcrumBaseURL + 'audio/' + fieldValue['audio_id'] + '/track.gpx', headers=self.fulcrumHeaders)
		if blob.status_code == 200:
			print 'Uploading Audio GPX Track To Salesforce... ' + recordId
			self.upload_file_to_salesforce_and_attach_to_record (recordId=recordId, fileTitle=fieldValue['audio_id'] + ' GPX Track', fileDescription='GPX Track Track Of\n' + fieldValue['caption'], fileName=fieldValue['audio_id'] + '-track.gpx', fileContent=blob.content)

		blob = requests.request ('GET', _fulcrumBaseURL + 'audio/' + fieldValue['audio_id'] + '/track.kml', headers=self.fulcrumHeaders)
		if blob.status_code == 200:
			print 'Uploading Audio KML Track To Salesforce... ' + recordId
			self.upload_file_to_salesforce_and_attach_to_record (recordId=recordId, fileTitle=fieldValue['audio_id'] + ' KML Track', fileDescription='KML Track Track Of\n' + fieldValue['caption'], fileName=fieldValue['audio_id'] + '-track.kml', fileContent=blob.content)
		return

	def process_date_field (self, fieldId, fieldValue):
		#Generate Date Time
		return self.process_generate_field (fieldId, fieldValue, 'Date')

	def process_datetime_field (self, record, isDateField, fieldId, fieldValue):
		#Generate Date Time
		# Check to see if the last field processed was a Date Field
		if isDateField != _isDateFieldDefault:
			dateValue = record['form_values'][isDateField]
			dateTimeValue = dateValue + ' ' + fieldValue
			return self.process_generate_field (isDateField + '_' + fieldId, dateTimeValue, 'DateTime')
		#Not paired with a Date Field
		else:
			return self.process_generate_field (fieldId, fieldValue, 'Time')

	def process_address_and_choice_field (self, fieldId, subFieldKey, subFieldValue):
		if subFieldValue == 'sub_thoroughfare':
			return self.process_generate_field (fieldId + '_1', subFieldValue, 'Street Number')
		
		elif subFieldKey == 'thoroughfare':
			return self.process_generate_field (fieldId + '_2', subFieldValue, 'Street Name')
		
		elif subFieldKey == 'suite':
			return self.process_generate_field (fieldId + '_3', subFieldValue, 'Suite')
		
		elif subFieldKey == 'locality':
			return self.process_generate_field (fieldId + '_4', subFieldValue, 'City')
		
		elif subFieldKey == 'sub_admin_area':
			return self.process_generate_field (fieldId + '_5', subFieldValue, 'County')
		
		elif subFieldKey == 'admin_area':
			return self.process_generate_field (fieldId + '_6', subFieldValue, 'State/Province')
		
		elif subFieldKey == 'postal_code':
			return self.process_generate_field (fieldId + '_7', subFieldValue, 'Postal Code')
		
		elif subFieldKey == 'country':
			return self.process_generate_field (fieldId + '_8', subFieldValue, 'Country')
		
		elif subFieldKey == 'choice_values':
			choices = []
			multiSelectChoices = subFieldValue[0]

			for choice in subFieldValue:
				choices.append (choice)
				if multiSelectChoices != choice:
					multiSelectChoices += ';' + choice
			if len(choices) == 1:
				self.process_generate_field (fieldId, choices, 'Choices')
			else:
				return self.process_generate_field (fieldId, multiSelectChoices, 'Multiselect Choices')

		elif subFieldKey == 'other_values':
			for choice in subFieldValue:
				return self.process_generate_field (fieldId, choice, 'Other Choice')

	# Determine the type of field and process it. This handles files.
	def detect_file_field_type_and_process_field (self, fieldId, record, recordId, detail=False):
		fieldValue = ''
		if detail == False:
			fieldValue = record['form_values'][fieldId]
		elif detail == True:
			fieldValue = record[fieldId]
		isDictField = isinstance (fieldValue, dict)
		isListField = isinstance (fieldValue, list)

		#print fieldValue

		if isListField == True:
			for complexFieldValue in fieldValue:
				#print complexFieldValue
				isComplexDictField = isinstance (complexFieldValue, dict)
				if isComplexDictField == True:
					isRepeatingSections = self.checkKey(complexFieldValue, 'form_values')
					isPhotoField = self.checkKey(complexFieldValue, 'photo_id')
					isVideoField = self.checkKey(complexFieldValue, 'video_id')
					isAudioField = self.checkKey(complexFieldValue, 'audio_id')

					if isPhotoField == True:
						print "Photo Field Detected..."
						return self.process_photo_field (complexFieldValue, recordId)
					elif isVideoField == True:
						print "Video Field Detected..."
						return self.process_video_field (complexFieldValue, recordId)
					elif isAudioField == True:
						print "Audio Field Detected..."
						return self.process_audio_field (complexFieldValue, recordId)
					elif isRepeatingSections == True:
						print "Child Record Detected..."
						return self.process_file_fields (complexFieldValue, recordId)

		elif isDictField == True:

			isSignatureField = self.checkKey(fieldValue, 'signature_id')
			
			if isSignatureField == True:
				print "Signature Field Detected..."
				return self.process_signature_field (fieldValue, recordId)
			

	# Determine the type of field and process it. This handles data.
	def detect_field_type_and_process_field (self, fieldId, record, isDateField=_isDateFieldDefault, detail=False):
		fieldValue = ''
		if detail == False:
			fieldValue = record['form_values'][fieldId]
		elif detail == True:
			fieldValue = record[fieldId]
		isListField = isinstance (fieldValue, list)
		isDictField = isinstance (fieldValue, dict)
		if isListField == True:
			for complexFieldValue in fieldValue:
				isRepeatingSections = self.checkKey(complexFieldValue, 'form_values')
				isDictComplexField = isinstance (complexFieldValue, dict)
				isJunctionObject = self.checkKey(complexFieldValue, 'record_id')

		elif isDictField == True:
			for subFieldKey in fieldValue:
				subFieldValue = fieldValue[subFieldKey]
				return self.process_address_and_choice_field (fieldId, subFieldKey, subFieldValue)

		# Date Time field
		elif re.match(r"([0-2][0-9]:[0-5][0-9])", fieldValue):
			return self.process_datetime_field (record, isDateField, fieldId, fieldValue)
		# Date field
		elif re.match(r"([1-2][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9])", fieldValue):
			#Mark that this loop was a Date, in prep for a Time Field
			isDateField = fieldId
			return self.process_date_field (fieldId, fieldValue)
		#easy field
		else:
			return self.process_generate_field (fieldId, fieldValue)

	def generate_junction_records (self, complexFormValues):
		return

	def generate_detail_fields (self, complexFormValues):
		dict (complexFormValues)
		sfdcFields = []

		for detailRecord in complexFormValues:
			isDateField = _isDateFieldDefault
			fieldAppend = self.detect_field_type_and_process_field (detailRecord, complexFormValues, isDateField, True)
			#print fieldAppend
			if isinstance (fieldAppend, dict):
				sfdcFields.append (fieldAppend)

			if isDateField != detailRecord:
				isDateField = _isDateFieldDefault

		sfdcFields = json.dumps (sfdcFields).replace('[','').replace(']','').replace('{','').replace('}','')

		return sfdcFields

	def generate_fields (self, record):
		sfdcFields = []
		isDateField = _isDateFieldDefault
		#print record
		for fieldId in record['form_values']:
			fieldAppend = self.detect_field_type_and_process_field (fieldId, record, isDateField)
			#print fieldAppend
			if isinstance (fieldAppend, dict):
				sfdcFields.append (fieldAppend)

		# If this Loop was not a Date Field, Reset Back to Default Value
		if isDateField != fieldId:
			isDateField = _isDateFieldDefault

		sfdcFields = json.dumps (sfdcFields).replace('[','').replace(']','').replace('{','').replace('}','')

		return sfdcFields

	def create_sfdc_fulcrum_record (self, record):
		objectId = (_sfdcPrefix + record['form_id'] + '__c').replace('-','_')
		sfdcCreateRecords = self.generate_sfdc_fulcrum_record (record)
		sfdcCreateRecords = json.loads(sfdcCreateRecords)
		return fulcrumToSalesforce.composite_salesforce_create (objectId, sfdcCreateRecords)

	def update_sfdc_fulcrum_record (self, record):
		objectId = (_sfdcPrefix + record['form_id'] + '__c').replace('-','_')
		sfdcObject = SFType (objectId, self.sfdc.session_id, self.sfdc.sf_instance)
		recordExists = sfdcObject.get_by_custom_id (_sfdcPrefix + 'fulcrum_id__c', record['id'])
		if recordExists:
			## Get Child Records
			for fieldId in record['form_values']:
				fieldValue = record['form_values'][fieldId]
				isListField = isinstance (fieldValue, list)
				if isListField == True:
					complexFieldType = fieldValue[0]
					isRepeatingSections = self.checkKey(complexFieldType, 'form_values')
					isJunctioonObject = self.checkKey(complexFieldType, 'record_id')
					if isRepeatingSections == True:
						objectId = _sfdcPrefix + record['form_id'][0:13].replace('-','_') + '_' + fieldId + '_d__c'
						objectReferenceId = _sfdcPrefix + record['form_id'][0:13].replace('-','_') + '_' + fieldId + '_d__r'
						sfdcInsertRecord = ''
						for complexFieldValue in fieldValue:
							detailRecordExists = sfdcObject.get_by_custom_id (_sfdcPrefix + 'fulcrum_id__c', complexFieldValue['id'])
							if detailRecordExists:
								sfdcRecordUpdate = generate_sfdc_fulcrum_detail_record (self, complexFieldValue)
								print sfdcRecordUpdate
								exit ()

			else:
				self.create_sfdc_fulcrum_record (record)


	def generate_sfdc_fulcrum_record (self, record):
		print '---------------------------------------'
		print 'Processing Fulcrum Record...'
		objectId = (_sfdcPrefix + record['form_id'] + '__c').replace('-','_')
		sfdcRecord = self.standard_fields_master_record (record)

		sfdcFields = self.generate_fields (record)

		objectIdString = '"' + objectId + '"'
		recordIdString = '"' + record['id'] + '"'

		sfdcRecord = json.dumps (sfdcRecord).replace('[','').replace(']','').replace('{','').replace('}','')

		sfdcDetailRecords = self.generate_sfdc_fulcrum_detail_records (record)

		if sfdcDetailRecords is None:

			sfdcRecord = """{"records": [{"attributes": {"type" : """ + objectIdString + """, "referenceId": """ + recordIdString + """ }, """ + sfdcRecord + ',' +  sfdcFields + """ }]}"""
		else:
			detailRecordJson = sfdcDetailRecords[0]
			for detailRecord in sfdcDetailRecords:
				if detailRecord != detailRecordJson:
					detailRecordJson += "," + detailRecordJson
			sfdcRecord = """{"records": [{"attributes": {"type" : """ + objectIdString + """, "referenceId": """ + recordIdString + """ }, """ + sfdcRecord + ',' +  sfdcFields + ', ' + detailRecordJson + """ }]}"""

		return sfdcRecord

	def generate_sfdc_fulcrum_detail_record (self, complexFieldValue):
		complexFormValues = complexFieldValue['form_values']

		sfdcFields = self.generate_detail_fields (complexFormValues)

		objectIdString = '"' + objectId + '"'
		recordIdString = '"' + complexFieldValue['id'] + '"'

		#sfdcRecord = json.dumps (sfdcRecord).replace('[','').replace(']','').replace('{','').replace('}','')
		sfdcRecord = json.dumps (sfdcRecord).replace('[','').replace(']','').replace('{','').replace('}','')

		sfdcRecord = """, { "attributes": {"type" : """ + objectIdString + """ , "referenceId": """ + recordIdString + """ }, """ + sfdcRecord + ',' + sfdcFields + """ }"""
		sfdcInsertRecord += sfdcRecord

	def standard_fields_master_record (self, record):
		sfdcRecord = []

		if record['status'] is not None:
			sfdcRecord.append (self.process_generate_field ('status', record['status'], 'Status'))

		if record['version'] is not None:
			sfdcRecord.append (self.process_generate_field ('version', record['version'], 'Version'))

		if record['id'] is not None:
			sfdcRecord.append (self.process_generate_field ('fulcrum_id', record['id'], 'Id'))

		if record['created_at'] is not None:
			sfdcRecord.append (self.process_generate_field ('created_at', record['created_at'], 'Created At'))

		if record['updated_at'] is not None:
			sfdcRecord.append (self.process_generate_field ('updated_at', record['updated_at'], 'Updated At'))

		if record['client_created_at'] is not None:
			sfdcRecord.append (self.process_generate_field ('client_created_at', record['client_created_at'], 'Client Created At'))

		if record['client_updated_at'] is not None:
			sfdcRecord.append (self.process_generate_field ('client_updated_at', record['client_updated_at'], 'Client Updated At'))

		if record['created_by'] is not None:
			sfdcRecord.append (self.process_generate_field ('created_by', record['created_by'], 'Created By'))

		if record['created_by_id'] is not None:
			sfdcRecord.append (self.process_generate_field ('created_by_id', record['created_by_id'], 'Created By Id'))

		if record['updated_by'] is not None:
			sfdcRecord.append (self.process_generate_field ('updated_by', record['updated_by'], 'Updated By'))

		if record['updated_by_id'] is not None:
			sfdcRecord.append (self.process_generate_field ('updated_by_id', record['updated_by_id'], 'Updated By Id'))

		if record['created_location'] is not None:
			sfdcRecord.append (self.process_generate_field ('created_location', record['created_location'], 'Created Location'))

		if record['updated_location'] is not None:
			sfdcRecord.append (self.process_generate_field ('updated_location', record['updated_location'], 'Updated Location'))

		if record['created_duration'] is not None:
			sfdcRecord.append (self.process_generate_field ('created_duration', record['created_duration'], 'Created Duration'))

		if record['updated_duration'] is not None:
			sfdcRecord.append (self.process_generate_field ('updated_duration', record['updated_duration'], 'Updated Duration'))

		if record['edited_duration'] is not None:
			sfdcRecord.append (self.process_generate_field ('edited_duration', record['edited_duration'], 'Edited Duration'))

		if record['project_id'] is not None:
			sfdcRecord.append (self.process_generate_field ('project_id', record['project_id'], 'Project Id'))

		if record['changeset_id'] is not None:
			sfdcRecord.append (self.process_generate_field ('changeset_id', record['changeset_id'], 'Change Set ID'))

		if record['assigned_to'] is not None:
			sfdcRecord.append (self.process_generate_field ('assigned_to', record['assigned_to'], 'Assigned To'))

		if record['assigned_to_id'] is not None:
			sfdcRecord.append (self.process_generate_field ('assigned_to_id', record['assigned_to_id'], 'Assigned To Id'))

		if record['form_id'] is not None:
			sfdcRecord.append (self.process_generate_field ('form_id', record['form_id'], 'Form Id'))

		if record['latitude'] is not None:
			sfdcRecord.append (self.process_generate_field ('location', record['latitude'], 'Latitude'))

		if record['longitude'] is not None:
			sfdcRecord.append (self.process_generate_field ('location', record['longitude'], 'Longitude'))

		if record['speed'] is not None:
			sfdcRecord.append (self.process_generate_field ('speed', record['speed'], 'Speed'))

		if record['course'] is not None:
			sfdcRecord.append (self.process_generate_field ('course', record['course'], 'Course'))

		if record['horizontal_accuracy'] is not None:
			sfdcRecord.append (self.process_generate_field ('horizontal_accuracy', record['horizontal_accuracy'], 'Horizontal Accuracy'))

		if record['vertical_accuracy'] is not None:
			sfdcRecord.append (self.process_generate_field ('vertical_accuracy', record['vertical_accuracy'], 'Vertical Accuracy'))

		return sfdcRecord

	def standard_fields_detail_record (self, complexFieldValue):
		sfdcRecord = []

		if complexFieldValue['version'] is not None:
			sfdcRecord.append (self.process_generate_field ('version', complexFieldValue['version'], 'Version'))

		if complexFieldValue['id'] is not None:
			sfdcRecord.append (self.process_generate_field ('fulcrum_id', complexFieldValue['id'], 'Id'))

		if complexFieldValue['created_at'] is not None:
			sfdcRecord.append (self.process_generate_field ('created_at', complexFieldValue['created_at'], 'Created At'))

		if complexFieldValue['updated_at'] is not None:
			sfdcRecord.append (self.process_generate_field ('updated_at', complexFieldValue['updated_at'], 'Updated At'))

		if complexFieldValue['created_by_id'] is not None:
			sfdcRecord.append (self.process_generate_field ('created_by_id', complexFieldValue['created_by_id'], 'Created By Id'))

		if complexFieldValue['updated_by_id'] is not None:
			sfdcRecord.append (self.process_generate_field ('updated_by_id', complexFieldValue['updated_by_id'], 'Updated By Id'))

		if complexFieldValue['created_duration'] is not None:
			sfdcRecord.append (self.process_generate_field ('created_duration', complexFieldValue['created_duration'], 'Created Duration'))

		if complexFieldValue['updated_duration'] is not None:
			sfdcRecord.append (self.process_generate_field ('updated_duration', complexFieldValue['updated_duration'], 'Updated Duration'))

		if complexFieldValue['edited_duration'] is not None:
			sfdcRecord.append (self.process_generate_field ('edited_duration', complexFieldValue['edited_duration'], 'Edited Duration'))

		if complexFieldValue['changeset_id'] is not None:
			sfdcRecord.append (self.process_generate_field ('changeset_id', complexFieldValue['changeset_id'], 'Change Set ID'))

		if complexFieldValue['geometry'] is not None:
			sfdcRecord.append (self.process_generate_field ('location', complexFieldValue['geometry']['coordinates'][1], 'Latitude'))
			sfdcRecord.append (self.process_generate_field ('location', complexFieldValue['geometry']['coordinates'][0], 'Longitude'))

		return sfdcRecord

	# Fulcrum Record and SFDC Parent Record ID (prefix and postfix added)
	def generate_sfdc_fulcrum_detail_records (self, record):
		print '.......................................'
		print 'Processing Fulcrum Detail Records...'
		sfdcRecords = []
		for fieldId in record['form_values']:
			fieldValue = record['form_values'][fieldId]
			isListField = isinstance (fieldValue, list)
			if isListField == True:
				complexFieldType = fieldValue[0]
				isRepeatingSections = self.checkKey(complexFieldType, 'form_values')
				if isRepeatingSections == True:
					sfdcInsertRecord = ''
					objectId = _sfdcPrefix + record['form_id'][0:13].replace('-','_') + '_' + fieldId + '_d__c'
					objectReferenceId = _sfdcPrefix + record['form_id'][0:13].replace('-','_') + '_' + fieldId + '_d__r'
					for complexFieldValue in fieldValue:
						print '.......................................'
						print 'Processing Detail Record...'
						print '   Object: ' + objectId
						print '   ReferenceName: ' + objectReferenceId
						sfdcRecord = self.standard_fields_detail_record (complexFieldValue)

						complexFormValues = complexFieldValue['form_values']

						sfdcFields = self.generate_detail_fields (complexFormValues)

						objectIdString = '"' + objectId + '"'
						recordIdString = '"' + complexFieldValue['id'] + '"'

						#sfdcRecord = json.dumps (sfdcRecord).replace('[','').replace(']','').replace('{','').replace('}','')
						sfdcRecord = json.dumps (sfdcRecord).replace('[','').replace(']','').replace('{','').replace('}','')

						sfdcRecord = """, { "attributes": {"type" : """ + objectIdString + """ , "referenceId": """ + recordIdString + """ }, """ + sfdcRecord + ',' + sfdcFields + """ }"""
						sfdcInsertRecord += sfdcRecord


					objectReferenceIdString = '"' + str(objectReferenceId) + '"'
					sfdcInsertRecord = sfdcInsertRecord.replace(',',"",1)
					recordJson = objectReferenceIdString + """:{"records":[""" + sfdcInsertRecord +"""]}"""

					sfdcRecords.append (recordJson)

		return sfdcRecords
