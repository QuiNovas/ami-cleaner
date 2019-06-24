*************
ami-cleaner
*************
Lambda function that can be scheduled to clean up old AMI's.

This function Deregisters the Private AMIs which are older than days specified by the user and deletes the corresponding EBS Snapshots.

It deletes the AMI only if:

- Not a Public AMI
 
- Not getting used in any of Autoscaling Launch Configurations. 

- Not getting used in any of the Launch Template versions 

- Has at least one latest copy.

**Environment variables**
OLDER_THAN_DAYS - *REQUIRED*

**IAM Permissions**

"ec2:DeleteSnapshot",

"ec2:DeregisterImage",

"ec2:DescribeImages",

"ec2:DescribeInstances",

"ec2:DescribeSnapshots",

"ec2:DescribeLaunchTemplateVersions",

"ec2:DescribeLaunchTemplates",

"autoscaling:DescribeAutoScalingGroups",

"autoscaling:DescribeLaunchConfigurations"


**Request Syntax**

{}

**Response Syntax**

[
  {
    "ami_id": "ami-028b77e3194f87c82",

    "snapshot_ids": [
      "snap-00aebf580f654890d",
      "snap-093f9c7abba4f0d94"
    ]
  },

  {
    "ami_id": "ami-05a0b31dbe028babc",

    "snapshot_ids": [
      "snap-093f9c7abba4f0d94"
    ]
  }
]