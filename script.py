from simple_salesforce import Salesforce
import numpy as np
import os, pandas, requests
from datetime import date, datetime, timedelta

# read values from the environment
LOGIN_URL=os.environ['LOGIN_URL']
CONSUMER_KEY=os.environ['CONSUMER_KEY']
CONSUMER_SECRET=os.environ['CONSUMER_SECRET']
BUSINESS_UNIT_ID=os.environ['BUSINESS_UNIT_ID']

DAYS_AGO=os.environ['DAYS_AGO'] #3650 # only used on the 1st run

SALESFORCE_OBJECT='Pardot_Activity__c'

# retrieve access token from Salesforce
access_token_response = requests.post(
    f'{LOGIN_URL}/services/oauth2/token',
    data={
        'grant_type':'client_credentials',
        'client_id': CONSUMER_KEY,
        'client_secret': CONSUMER_SECRET
    }
)
oauth_token = access_token_response.json()
authHeaders = {
    'Authorization': f'Bearer {oauth_token["access_token"]}',
    'Pardot-Business-Unit-Id': BUSINESS_UNIT_ID
}
sf = Salesforce(session_id=oauth_token["access_token"], instance_url=LOGIN_URL)


# get the last visitor activity from Salesforce
soqlQuery = 'SELECT MAX(Activity_Id__c) FROM Pardot_Activity__c'
queryResponse = sf.query(soqlQuery)

if queryResponse['done']:
  lastId = int(queryResponse['records'][0]['expr0'])
  print(f'Using Id {lastId} from Salesforce')
else:
  print(f'Could not find lastId from Salesforce, assuming first run')
  lastId= None


  # get the data from the Visitor Activity Query API
all_query_data = []
needToMakeQuery=True
queryUrl='https://pi.pardot.com/api/v5/objects/visitor-activities'
queryParams= {
    'limit': 1000,
    #'fields':'id,campaignId,campaign.name,customRedirectId,customRedirect.name,details,emailId,emailTemplateId,emailTemplate.name,email.name,fileId,file.name,formHandlerId,formHandler.name,formId,form.name,landingPageId,landingPage.name,listEmailId,listEmail.name,multivariateTestVariationId,paidSearchAdId,prospectId,prospect.salesforceId,siteSearchQueryId,typeName,type,updatedAt,visitId,visitorId'
    'fields':'id,campaignId,campaign.name,campaign.salesforceId,details,prospectId,prospect.salesforceId,typeName,type,createdAt',
    'prospectIdGreaterThan': 1
}
if lastId==None:
  print(f'We cant tell what the last run id was, going back {DAYS_AGO} days')
  targetDate = date.today() - timedelta(days=DAYS_AGO)
  queryParams['updatedAtAfterOrEqualTo'] = targetDate.isoformat() + 'T00:00:00-04:00'
else:
  print('Resuming from the last gathered VisitorActivity record')
  queryParams['idGreaterThan']=lastId

apiCallsMade=0

while needToMakeQuery:
  apiCallsMade +=1
  print(f'Req: {apiCallsMade} - making GET request to: {queryUrl}')
  query_response = requests.get(
      url=queryUrl,
      params=queryParams,
      headers=authHeaders
  ).json()
  # print(query_response)

  all_query_data += query_response['values']

  if 'nextPageUrl' in query_response and query_response['nextPageUrl']:
    queryUrl = query_response['nextPageUrl']
    queryParams={} # clear the params out, as it is built into nextPageUrl
    # print('Making another API call to get more Visitor Activity Records')
  else:
    needToMakeQuery=False

visitorActivityCount = len(all_query_data)
if visitorActivityCount == 0:
  print('There are no activity records to process today')
  exit(0)

print(f'Done getting {visitorActivityCount} records from Pardot')

print('Starting to Transform and Process the data collected')
# map some of the data if required
dataframe = pandas.json_normalize(all_query_data, sep='_') # throw collected data into Dataframe
# drop records that have no SalesforceId
dataframe.dropna(subset=['prospect_salesforceId'], inplace=True)
# print('before manipulations')
# print(dataframe.head(10))

# build type map from Integer to Description
typeMap = dict([(1,'Click'),(2, 'View'),(3,'Error'),(4,'Success'),(5,'Session'),
                (6,'Sent'),(7,'Search'),(8,'New Opportunity'),(9,'Opportunity Won'),
                (10,'Opportunity Lost'),(11,'Open'),(12,'Unsubscribe Page'),
                (13,'Bounced'),(14,'Spam Complaint'),(15,'Email Preference Page'),
                (16,'Resubscribed'),(17,'Click (Third Party)'),(18,'Opportunity Reopened'),
                (19,'Opportunity Linked'),(20,'Visit'),(21,'Custom URL Click'),
                (22,'Olark Chat'),(23,'Invited to Webinar'),(24,'Attended Webinar'),
                (25,'Registered for Webinar'),(26,'Social Post Click'),(27,'Video View'),
                (28,'Event Registered'),(29,'Event Checked In'),(30,'Video Conversion'),
                (31,'UserVoice Suggestion'),(32,'UserVoice Comment'),(33,'UserVoice Ticket'),
                (34,'Video Watched (> 75% watched)'),(35,'Indirect Unsubscribe Open'),
                (36,'Indirect Bounce'),(37,'Indirect Resubscribed'),(38,'Opportunity Unlinked')])

dataframe = dataframe.replace({'type':typeMap})
dataframe = dataframe.rename(columns={
    'id':'Activity_Id__c',
    'campaignId':'Pardot_CampaignID__c',
    'createdAt':'CreatedDate',
    'details':'Details__c',
    'type':'Type__c',
    'typeName':'Type_Name__c',
    'campaign_name':'Campaign_Name__c',
    'campaign_salesforceId':'Campaign__c'
})

dataframe['Lead__c'] = dataframe.apply(lambda x: x['prospect_salesforceId'] if x['prospect_salesforceId'].startswith('00Q') else None, axis=1)
dataframe['Contact__c'] =  dataframe.apply(lambda x: x['prospect_salesforceId'] if x['prospect_salesforceId'].startswith('003') else None, axis=1)
# get rid of columns we don't want anymore
dataframe = dataframe.drop(['prospectId','prospect_salesforceId','campaign'], axis=1)
dataframe['Pardot_CampaignID__c'] = dataframe['Pardot_CampaignID__c'].astype('Int64')
# print(dataframe.head())
# print(dataframe.head().to_dict(orient='records'))

print(f'Transformations complete, starting to send {len(dataframe)} records to Salesforce')

# Send our results to Salesforce
sdf = dataframe.fillna(np.nan).replace([np.nan], [None])
list_of_records = sdf.to_dict(orient='records')
sf.bulk.Pardot_Activity__c.insert(list_of_records)

print('Data sent to Salesforce. Script completed successfully')