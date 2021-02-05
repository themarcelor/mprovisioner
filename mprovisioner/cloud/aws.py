import boto3
from cloud.api import APIHandler

class AWSAPIHandler(APIHandler):

  def provision_vms(self):
    print('test')
    # testing boto3
    ec2_client = boto3.client('ec2')
    response = ec2_client.describe_instances()
    print(f'resp: {response}')
