import boto3
import json
import os
import ssl
import urllib.error
from socket import timeout
from urllib.request import Request, urlopen

dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')
sns = boto3.client('sns')


def main(event, context):
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    sites = table.scan()
    for site in sites['Items']:
        siteInfo = {"url": site['url']}
        lambda_client.invoke(
            FunctionName="site-monitor-ping-"+os.environ['SERVERLESS_STAGE'],
            InvocationType='Event',
            Payload=json.dumps(siteInfo),
        )    

def ping(event, context):
    # Disable SSL warnings
    ssl_context = ssl._create_unverified_context()
    site = event['url']
    try:
        req = Request(site, headers={
                    'User-Agent': 'CKA Site Monitor'})
        status = urlopen(req, context=ssl_context, timeout=5).getcode()
    except (urllib.error.URLError, timeout) as e:
        status = 600
        reason = e.reason

    if status > 302:
        topicArn = os.environ['SNS_ALERT']
        sns.publish(
            TopicArn = topicArn,
            Subject = "Website Monitor - Issue Detected",
            Message = "We are not able to connect to %s please verify the site is working correctly!\nSTATUS: %s\nREASON: %s" % (site, status, reason)
        )            