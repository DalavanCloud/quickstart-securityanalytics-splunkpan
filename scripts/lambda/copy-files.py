import json
import boto3
from botocore.vendored import requests
import logging
from xml.etree.ElementTree import parse, Element
from botocore.exceptions import ClientError

print('Loading function')

# Initialize boto client
s3 = boto3.client('s3')

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Define variables
SUCCESS = "SUCCESS"
FAILED = "FAILED"

bootstrap_xml = 'bootstrap.xml'
init_config = 'init-cfg.txt'
target_bootstrap_xml = 'config/' + bootstrap_xml
target_init_config = 'config/' + init_config
target_license = 'license/'
target_software = 'software/'
target_content = 'content/'

def lambda_handler(event, context):
    #print("Received event: " + json.dumps(event, indent=2))
    try:
        target_bucket = event['ResourceProperties']['TargetBucket']
        source_bucket = event['ResourceProperties']['SourceBucket']
        keyprefix = 'config/'
            
        if event['RequestType'] == 'Create':
            logger.info("RequestType: CREATE")
            
            s3bucket = source_bucket
            s3keyprefix = "config/"
            filename = "bootstrap.xml"
            splunk_hostname = event['ResourceProperties']['splunk_hostname']
            splunk_port = event['ResourceProperties']['splunk_port']
            splunk_transport = event['ResourceProperties']['splunk_transport']
        
            logger.info('s3 object path {}/{}{}'.format(s3bucket, s3keyprefix, filename))
            # Download fil locally
            key = '{}{}'.format(s3keyprefix, filename)
            download_path = '/tmp/{}'.format(filename)
            s3.download_file(s3bucket, key, download_path)
            logger.info('File downloaded')
            # Find root element 'config'
            doc = parse(download_path)
            root = doc.getroot()
            logger.debug('root = {}'.format(root))
            # Find splunk hostname element and update value
            e_splunk_server = root.findall("./shared/log-settings/syslog/entry/server/entry/server")[0]
            if e_splunk_server != None and e_splunk_server.text == 'HOSTNAME-REPLACE-ME':
                e_splunk_server.text = str(splunk_hostname)
            else:
                logger.error('splunk server element not found')
                status = FAILED
            # Find splunk port element and update value
            e_splunk_port = root.findall("./shared/log-settings/syslog/entry/server/entry/port")[0]
            if e_splunk_port != None and e_splunk_port.text == 'PORT-REPLACE-ME':
                e_splunk_port.text = str(splunk_port)
            else:
                logger.error('splunk port element not found')
                status = FAILED
            # Find splunk transport element and update value
            e_splunk_transport = root.findall("./shared/log-settings/syslog/entry/server/entry/transport")[0]
            if e_splunk_transport != None and e_splunk_transport.text == 'TRANSPORT-REPLACE-ME':
                e_splunk_transport.text = str(splunk_transport)
            else:
                logger.error('splunk transport element not found')
                status = FAILED
                
            # Write back to a file
            doc.write(download_path, encoding='utf-8', xml_declaration=True)
            # Upload file back to S3
            s3.upload_file(download_path, target_bucket, '{}{}'.format(s3keyprefix, filename), ExtraArgs={'ACL': 'public-read'})
            
            
            # Copy init-config.txt file
            copy_source = {'Bucket':source_bucket, 'Key':keyprefix + init_config}
            logger.debug("Copying {} from bucket {} to bucket {} ...".format(keyprefix + init_config, source_bucket, target_bucket))
            s3.copy_object(ACL='public-read', Bucket=target_bucket, Key=target_init_config, CopySource=copy_source)
            # Create license folder
            logger.debug("Creating {} folder in {} bucket ...".format(target_license, target_bucket))
            s3.put_object(ACL='public-read', Bucket=target_bucket, Body='', Key=target_license)
            # Create software folder
            logger.debug("Creating {} folder in {} bucket ...".format(target_software, target_bucket))
            s3.put_object(ACL='public-read', Bucket=target_bucket, Body='', Key=target_software)
            # Create content folder
            logger.debug("Creating {} folder in {} bucket ...".format(target_content, target_bucket))
            s3.put_object(ACL='public-read', Bucket=target_bucket, Body='', Key=target_content)
            
            status = SUCCESS
        
        elif event['RequestType'] == 'Delete':
            logger.info("RequestType: DELETE")
            
            # Delete bootstrap.xml file
            logger.debug("Deleteing {}".format(target_bucket + "/" + keyprefix + bootstrap_xml))
            s3.delete_object(Bucket=target_bucket, Key=target_bootstrap_xml)
            # Delete init-cfg.txt file
            logger.debug("Deleteing {}".format(target_bucket + "/" + keyprefix + init_config))
            s3.delete_object(Bucket=target_bucket, Key=target_init_config)
            # Delete license folder
            logger.debug("Deleteing {}".format(target_bucket + "/" + target_license))
            s3.delete_object(Bucket=target_bucket, Key=target_license)
            # Delete software folder
            logger.debug("Deleteing {}".format(target_bucket + "/" + target_software))
            s3.delete_object(Bucket=target_bucket, Key=target_software)
            # Delete content folder
            logger.debug("Deleteing {}".format(target_bucket + "/" + target_content))
            s3.delete_object(Bucket=target_bucket, Key=target_content)
            
            status = SUCCESS
            
    except Exception as e:
        logger.error("An error ocurred when executing the lambda function..." + str(e))
        status = FAILED
    
    finally:
        responseValue = "done"
        responseData = {}
        responseData['msg'] = responseValue
        send(event, context, status, responseData, "CustomResourcePhysicalID")
        # return 'SUCCESS'  # Echo back the first key value
        #raise Exception('Something went wrong')

def send(event, context, responseStatus, responseData, physicalResourceId=None):
    responseUrl = event['ResponseURL']

    logger.debug(responseUrl)

    responseBody = {}
    responseBody['Status'] = responseStatus
    responseBody['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
    responseBody['PhysicalResourceId'] = physicalResourceId or context.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['Data'] = responseData

    json_responseBody = json.dumps(responseBody)

    logger.debug("Response body:\n" + json_responseBody)

    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }

    try:
        response = requests.put(responseUrl,
                                data=json_responseBody,
                                headers=headers)
        logger.debug("Status code: " + response.reason)
    except Exception as e:
        logger.error("send(..) failed executing requests.put(..): " + str(e))