import boto3
import logging
import os
import time
import json
import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
autoscaling_client = boto3.client('autoscaling')

OLDER_THAN_DAYS = int(os.environ['OLDER_THAN_DAYS'])

def handler(event, context):
    response = ami_list(
        ec2_client.describe_images(
            Owners = ['self'])
        )
	#Response contains AMI ID's and there corresponding Snapshots which are removed
    return response

def ami_list(ami_list):
    response = []
    for items in ami_list['Images']:
        is_expired = expire(items['ImageId'], items['CreationDate'])
        if is_expired: 
            response.append(is_expired)
    return response	
	
	    
def expire(ami_id, creation_date):
    ami_ids = []
    date_now = datetime.datetime.utcnow().date()
    creation_date_only = datetime.datetime.strptime(creation_date, "%Y-%m-%dT%H:%M:%S.%fZ").date()

    if (date_now - creation_date_only).days > OLDER_THAN_DAYS:
        if(check_launch_configurations(ami_id) and check_launch_templates(ami_id)):
            logger.info('Will Deregister AMI {}'.format(ami_id))
            ami_ids.append(ami_id)
            deregister_data = deregister_image(ami_id)
            return ami_ids, deregister_data
        
def check_launch_configurations(ami_id):
    launch_configurations = autoscaling_client.describe_launch_configurations()
    for items in launch_configurations['LaunchConfigurations']:
        if ami_id == items['ImageId']:
            logger.info("{} Getting used in launch configurations, Will not be removed.".format(ami_id))
            return False
    return True
    
def check_launch_templates(ami_id):
    launch_templates = ec2_client.describe_launch_templates()
    for items in launch_templates['LaunchTemplates']:
	    if not (check_launch_template_versions(items['LaunchTemplateId'], ami_id)):
		    logger.info("{} Getting used in one or more launch template versions, Will not be removed.".format(ami_id))
		    return False
    return True
	
def check_launch_template_versions(launch_template_id, ami_id):
    response = ec2_client.describe_launch_template_versions(
	    LaunchTemplateId=launch_template_id)
    for items in response['LaunchTemplateVersions']:
        if ami_id == items['LaunchTemplateData']['ImageId']:            
            return False
    return True
	
def deregister_image(ami_id):
	snapshots = []
	
	#Get the SnapshotIDs before deleting the AMI.
	for items in ami_info_dump['Images']:
	    if ami_id == items['ImageId']:
		    for blockDeviceMappings in items['BlockDeviceMappings']:
			    snapshots.append(blockDeviceMappings['Ebs']['SnapshotId'])
	#Deregistering AMI			
	logger.info("Removing AMI {}".format(ec2_client.deregister_image(ImageId=ami_id)))
	
	#Deleting all ebs snapshots of the AMI
	for items in snapshots:
	    logger.info("Removing snapshot {}".format(ec2_client.delete_snapshot(SnapshotId=items)))
	return snapshots