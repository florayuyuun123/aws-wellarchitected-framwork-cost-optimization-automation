# Stop Burning Money: How I Automated AWS Cost Governance

*By [Your Name]*

If there is one thing that haunts every engineering team on AWS, it's the dreaded end-of-month bill. You log in to the billing console and wonder, "Why are we paying for 50 unattached EBS volumes? Who left these EC2 instances running over the weekend?"

As a Solutions Architect, I see this pattern constantly. It is an anti-pattern against the **Cost Optimization Pillar** of the AWS Well-Architected Framework. Manual cleanup works, but it doesn't scale. What you need is **Automated Cost Governance**.

In this article, I will walk you through a project I built to deliberately deploy wasteful infrastructure on AWS, detect the anomalies, and use AWS Systems Manager (SSM) Automation to clean it up automatically.

## The Problem: Unchecked Waste
I started by creating a CloudFormation template that provisions the "usual suspects" of AWS waste:
1. **Unattached EBS Volumes**: Developers terminate an EC2 instance but forget to delete the attached volumes.
2. **Idle EC2 Instances**: Servers spun up for a quick test and left running indefinitely.
3. **Inefficient S3 Buckets**: Storage buckets without lifecycle policies.

*(Insert Architecture Diagram Here)*

## The Solution: Detection and Remediation
To fix this, I implemented an automated pipeline leveraging Python (Boto3) and AWS SSM.

### 1. Detection via CloudWatch & Trusted Advisor
AWS Trusted Advisor is fantastic for identifying cost optimization opportunities, such as low-utilization EC2 instances and unattached EBS volumes. I set up CloudWatch alarms to trigger based on billing thresholds and Trusted Advisor metrics.

### 2. Remediation via SSM Automation
The core of the project is a custom AWS Systems Manager (SSM) Automation Document. I embedded a Python script within this document that performs two main tasks:

```python
# Snippet showing the logic to snapshot and delete unattached volumes
def cleanup_unattached_volumes(ec2_client):
    volumes = ec2_client.describe_volumes(Filters=[{'Name': 'status', 'Values': ['available']}])['Volumes']
    for volume in volumes:
        vol_id = volume['VolumeId']
        # Always snapshot before deleting!
        ec2_client.create_snapshot(VolumeId=vol_id, Description=f"Auto-snapshot {vol_id}")
        ec2_client.delete_volume(VolumeId=vol_id)
```

By wrapping this Boto3 script inside an SSM Document, we remove the need to deploy and manage lambda functions or schedule cron jobs on EC2. SSM handles the execution and logging securely.

### 3. Governance and Alerting via SNS
Nobody wants a script blindly deleting resources without a trace. The automation role is strictly scoped using IAM to only touch resources tagged appropriately, and an SNS notification is sent immediately after remediation, summarizing exactly what was deleted or stopped.

## Conclusion
Cost Optimization isn't a one-time event; it's a continuous process. By automating the cleanup of unattached volumes and idle instances, we bring our infrastructure back in line with the AWS Well-Architected Framework.

If you want to deploy this demo yourself, check out the code in my GitHub repository: [Link to Repo]

*Follow me on LinkedIn for more AWS architecture deep dives!*
