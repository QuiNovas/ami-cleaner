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
	ami_info = ec2_client.describe_images(Owners = ['self'])
	response = ami_list(ami_info)
	#Response contains a list of maps with ami and snapshot_ids as keys which will be deleted.
	return response

def ami_list(ami_list):
	response = []
	for items in ami_list['Images']:
		#Do not delete public amis
		if not items['Public']:
			is_expired = expire(items['ImageId'], items['CreationDate'])
			if is_expired: 
				response.append(is_expired)
	return response	
		
def expire(ami_id, creation_date):
	date_now = datetime.datetime.utcnow().date()
	creation_date_only = datetime.datetime.strptime(creation_date, "%Y-%m-%dT%H:%M:%S.%fZ").date()

	# Check if Expired
	if (date_now - creation_date_only).days > OLDER_THAN_DAYS:
		# Delete only if AMI is not getting used anywhere and atleast one other build exists
		if(check_launch_configurations(ami_id) and check_launch_templates(ami_id)) and check_if_atleast_one_previous_build(ami_id):
			logger.info('Will Deregister AMI {} Age {} days'.format(ami_id, (date_now - creation_date_only).days))
			return deregister_image(ami_id)

def check_if_atleast_one_previous_build(ami_id):
	complete_ami_list = ec2_client.describe_images(Owners = ['self'])

	"""Get the Name of the AMI without the isotime postfix
	Cut the last 14 characters
	For e.g amzn-ami-minimal-hvm-selinux-20200201000052 --> amzn-ami-minimal-hvm-selinux-
    """
	current_ami_name = ec2_client.describe_images(Owners = ['self'], ImageIds=[ami_id])['Images'][0]['Name'][:-14]
	current_ami_creation_date = ec2_client.describe_images(Owners = ['self'], ImageIds=[ami_id])['Images'][0]['CreationDate']
	current_ami_id = ami_id

	for items in ec2_client.describe_images(Owners = ['self'])['Images']:
		if (items['Name'][:-14] == current_ami_name) and (items['ImageId'] != current_ami_id):
			if compare_others(current_ami_id, current_ami_creation_date, items['ImageId'], items['CreationDate']):
				return True 

	return False

def compare_others(current_ami_id, current_ami_creation_date, other_ami_id, other_ami_creation_date):
	date_now = datetime.datetime.utcnow().date()
	other_ami_creation_date_only = datetime.datetime.strptime(other_ami_creation_date, "%Y-%m-%dT%H:%M:%S.%fZ").date()

	current_ami_creation_date = datetime.datetime.strptime(current_ami_creation_date, "%Y-%m-%dT%H:%M:%S.%fZ")
	other_ami_creation_date = datetime.datetime.strptime(other_ami_creation_date, "%Y-%m-%dT%H:%M:%S.%fZ")

	if (current_ami_creation_date < other_ami_creation_date):
		### If the other build is not older than current AMI, then delete the current AMI
		return True
	else:
		### If the other build is older than current AMI, then delete the older AMI
		if (check_launch_configurations(other_ami_id) and check_launch_templates(other_ami_id)):
			logger.info('Will Deregister the oldest build AMI {} Age {} days'.format(other_ami_id,(date_now - other_ami_creation_date_only).days))
			deregister_image(other_ami_id)
			
		return False

def check_launch_configurations(ami_id):
	launch_configurations = autoscaling_client.describe_launch_configurations()
	for items in launch_configurations['LaunchConfigurations']:
		if ami_id == items['ImageId']:
			logger.info("{} Getting used in one or more launch configurations, Will not be removed.".format(ami_id))
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
	final_response = {}
	snapshots = []
	response = ec2_client.describe_images(Owners = ['self'])
	#Get the SnapshotIDs before deleting the AMI.
	for items in response['Images']:
		if ami_id == items['ImageId']:
			for blockDeviceMappings in items['BlockDeviceMappings']:
				snapshots.append(blockDeviceMappings['Ebs']['SnapshotId'])
	#Deregistering AMI			
	logger.info("Removing AMI {}".format(ec2_client.deregister_image(ImageId=ami_id)))
	final_response['ami_id'] = ami_id
	final_response['snapshot_ids'] = snapshots
	
	#Deleting all ebs snapshots of the AMI
	for items in snapshots:
		logger.info("Removing snapshot {}".format(ec2_client.delete_snapshot(SnapshotId=items)))
	return final_response