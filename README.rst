# ami-cleaner
Lambda function that can be scheduled to clean up Old AMI's

This function Deregisters the AMIs which are older than days specified by the user and deletes the corresponding EBS Snapshots.
It only deletes the AMI, if it not getting used in any of Autoscaling Launch Configurations or in any versions of Launch Templates.

## Environment variables
OLDER_THAN_DAYS - **REQUIRED**

## IAM Permissions
"ec2:DeleteSnapshot",
"ec2:DeregisterImage",
"ec2:DescribeImages",
"ec2:DescribeInstances",
"ec2:DescribeSnapshots",
"ec2:DescribeLaunchTemplateVersions",
"ec2:DescribeLaunchTemplates",
"autoscaling:DescribeAutoScalingGroups",
"autoscaling:DescribeLaunchConfigurations"

## Request Syntax
{}

## Response Syntax
[
    [
        ami-02c0104a1da586915,
        snap-07bd03b0d5b52c848
    ],
]
