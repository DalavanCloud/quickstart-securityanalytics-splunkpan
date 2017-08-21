# AWS Lambda function file
# This is a lambda function to update the contents of an xml file in an S3 bucket

import logging
import boto3
from botocore.exceptions import ClientError
import cfnresponse
from xml.etree.ElementTree import parse, Element

s3_client = boto3.client('s3')

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def handler(event, context):
    logger.debug('event = {}'.format(event))
    
    if event['RequestType'] == 'Delete':
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, "CustomResourcePhysicalID")
    
    try:
        s3bucket = event['ResourceProperties']['xmlfile_bucket']
        s3keyprefix = event['ResourceProperties']['xmlfile_keyprefix']
        filename = event['ResourceProperties']['xmlfile_name']
        splunk_hostname = event['ResourceProperties']['splunk_hostname']
        splunk_port = event['ResourceProperties']['splunk_port']
        splunk_transport = event['ResourceProperties']['splunk_transport']
        
        logger.info('s3 object path {}/{}{}'.format(s3bucket, s3keyprefix, filename))
        # Download fil locally
        key = '{}{}'.format(s3keyprefix, filename)
        download_path = '/tmp/{}'.format(filename)
        s3_client.download_file(s3bucket, key, download_path)
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
            cfnresponse.send(event, context, cfnresponse.FAILED, {}, "CustomResourcePhysicalID")
        # Find splunk port element and update value
        e_splunk_port = root.findall("./shared/log-settings/syslog/entry/server/entry/port")[0]
        if e_splunk_port != None and e_splunk_port.text == 'PORT-REPLACE-ME':
            e_splunk_port.text = str(splunk_port)
        else:
            logger.error('splunk port element not found')
            cfnresponse.send(event, context, cfnresponse.FAILED, {}, "CustomResourcePhysicalID")
        # Find splunk transport element and update value
        e_splunk_transport = root.findall("./shared/log-settings/syslog/entry/server/entry/transport")[0]
        if e_splunk_transport != None and e_splunk_transport.text == 'TRANSPORT-REPLACE-ME':
            e_splunk_transport.text = str(splunk_transport)
        else:
            logger.error('splunk transport element not found')
            cfnresponse.send(event, context, cfnresponse.FAILED, {}, "CustomResourcePhysicalID")
            
        # Write back to a file
        doc.write(download_path, encoding='utf-8', xml_declaration=True)
        # Upload file back to S3
        s3_client.upload_file(download_path, s3bucket, '{}{}'.format(s3keyprefix, filename))
        
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, "CustomResourcePhysicalID")
    except Exception as err:
        logger.error(err)
        cfnresponse.send(event, context, cfnresponse.FAILED, {}, "CustomResourcePhysicalID")