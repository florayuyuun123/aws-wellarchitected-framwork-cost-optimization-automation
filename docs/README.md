# Automated Cost Governance on AWS

This Comprehensive Documentation Folder contains the architectural details, cost optimization strategies, and deployment guides for the "Automated Cost Governance on AWS" project. This project aligns with the **Cost Optimization Pillar** of the AWS Well-Architected Framework.

## Objective
To demonstrate how Solutions Architects identify and eliminate unnecessary AWS costs using automation.

## Architecture & Workflow
1. **Deliberate Waste**: A CloudFormation stack provisions wasteful resources (e.g., unattached EBS volumes, idle EC2 instances) to simulate a real-world, unoptimized environment.
2. **Detection**: AWS Trusted Advisor and CloudWatch metrics identify cost anomalies and unused resources.
3. **Governance & Automation**: EventBridge rules automatically intercept alerts from CloudWatch and Trusted Advisor. IAM Roles and SNS Topics are configured for secure execution and administrator alerting.
4. **Remediation**: AWS Systems Manager (SSM) Automation Documents, triggered automatically by EventBridge, execute Python (Boto3) scripts to clean up resources (snapshot and delete unattached volumes, stop idle instances).

## Project Structure
- `cloudformation/`: Contains the IaC templates for both the wasteful infrastructure and the governance setup.
- `ssm_automation/`: Contains the SSM Automation documents and the embedded Python cleanup logic.
- `TroubleshootingGuide.md`: A living document capturing issues encountered during deployment and execution.

## Deployment Guide

You can deploy the infrastructure using the following bash commands with the AWS CLI.

### 1. Deploy Wasteful Infrastructure
```bash
aws cloudformation create-stack \
  --stack-name flo-tech-WastefulInfra \
  --template-body file://cloudformation/wasteful_infrastructure.yaml \
  --parameters ParameterKey=EnvironmentName,ParameterValue=flo-tech \
  --region us-east-1
```
*(Wait for completion before proceeding)*

### 2. Deploy Governance Setup
```bash
aws cloudformation create-stack \
  --stack-name flo-tech-Governance \
  --template-body file://cloudformation/governance_setup.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters ParameterKey=NotificationEmail,ParameterValue=prettyflo02@gmail.com \
  --region us-east-1
```
*(Check your email to confirm the SNS subscription)*

### 3. Register SSM Automation Document
```bash
aws ssm create-document \
  --name "flo-tech-CostGovCleanup" \
  --document-type "Automation" \
  --document-format YAML \
  --content file://ssm_automation/cleanup_document.yaml \
  --region us-east-1
```

### 4. On-Demand / Testing Remediation (Manual Trigger)
While CloudWatch billing alarms and Trusted Advisor checks now serve as our fully automated triggers via EventBridge, you can execute the remediation manually to see the optimization in action immediately:
```bash
aws ssm start-automation-execution \
  --document-name "flo-tech-CostGovCleanup" \
  --parameters "AutomationAssumeRole=$(aws iam get-role --role-name flo-tech-CostGovSSMRole --query 'Role.Arn' --output text),SNSTopicArn=$(aws sns list-topics --query 'Topics[?contains(TopicArn, `flo-tech-CostGovAlert`)].TopicArn' --output text)" \
  --region us-east-1
```

## Verify Governance is Active

### 1. Confirm CloudWatch Billing Alarm
```bash
aws cloudwatch describe-alarms \
  --query "MetricAlarms[?contains(AlarmName, 'flo-tech')].[AlarmName,StateValue,Threshold]" \
  --output table --region us-east-1
```
**Expected:** `INSUFFICIENT_DATA` initially (billing metrics update once or twice per day), then `OK` or `ALARM` once data is collected. `ALARM` means the $10 threshold was breached and EventBridge will trigger the SSM automation.

### 2. Confirm EventBridge Rules are Enabled
```bash
aws events list-rules \
  --query "Rules[?contains(Name, 'flo-tech')].[Name,State,ScheduleExpression]" \
  --output table --region us-east-1
```
**Expected:** Both `CloudWatchAlarmEventRule` and `TrustedAdvisorEventRule` should show `ENABLED`.

### 3. Trusted Advisor
Trusted Advisor API requires a Business, Enterprise On-Ramp, or Enterprise support plan. If on free tier, check cost optimization findings directly in the [Trusted Advisor Console](https://console.aws.amazon.com/trustedadvisor).

### 4. Confirm S3 Lifecycle Policy was Applied
```bash
aws s3api get-bucket-lifecycle-configuration \
  --bucket flo-tech-inefficient-logs-$(aws sts get-caller-identity --query Account --output text)-us-east-1
```
**Expected:** Returns the lifecycle rules (Glacier transition after 30 days, expiration after 365 days) once SSM automation has run. If automation hasn't run yet, returns `NoSuchLifecycleConfiguration`.

---

## Verification & Waste Analysis

Once the `flo-tech-WastefulInfra` stack is deployed, you can verify the wasteful resources using the following bash commands:

### 1. Verify the Idle EC2 Instance
```bash
aws ec2 describe-instances --filters "Name=tag:Status,Values=Idle" --query "Reservations[*].Instances[*].[InstanceId,State.Name]" --output table --region us-east-1

```
**Why it's wasteful:** This instance (e.g., a `t3.medium`) is running but is serving no traffic. It's tagged as 'Idle', which simulates a development server left on over the weekend or a forgotten test environment. You are being billed per hour for a resource providing zero business value.

### 2. Verify the Unattached EBS Volume
```bash
aws ec2 describe-volumes \
  --filters "Name=status,Values=available" "Name=tag:Status,Values=Unattached" \
  --query "Volumes[*].[VolumeId,Size,VolumeType]" \
  --output table \
  --region us-east-1
```

### Check that a backup Snapshot was created before deletion:
```bash
aws ec2 describe-snapshots --owner-ids self --query "Snapshots[?contains(Description, 'Auto-snapshot')].[SnapshotId,Description]" --output table --region us-east-1
```

**Why it's wasteful:** An EBS volume with the status `available` means it is **not attached** to any EC2 instance. Even though it's not being used, AWS still charges you for the provisioned storage per GB-month. This frequently happens when an EC2 instance is terminated but the developer forgets to check the box to delete the attached EBS volumes.

### 3. Verify the Inefficient S3 Bucket
```bash
aws s3api list-buckets \
  --query "Buckets[?contains(Name, 'inefficient-logs')].[Name]" \
  --output table
```
**Why it's wasteful:** Storing logs in an S3 Standard tier indefinitely gets expensive. A well-architected environment would use S3 Lifecycle Policies to automatically move older logs to cheaper storage tiers (like Glacier) or delete them entirely after a set period.
## Teardown Guide

To ensure you do not incur lingering charges, clean up the resources with these bash commands:

```bash
aws cloudformation delete-stack --stack-name flo-tech-WastefulInfra --region us-east-1
aws cloudformation delete-stack --stack-name flo-tech-Governance --region us-east-1
aws ssm delete-document --name "flo-tech-CostGovCleanup" --region us-east-1
```
## Cost Optimization Strategies Demonstrated
- Identifying and cleaning up unattached EBS volumes.
- Stopping idle EC2 instances.
- Using S3 lifecycle policies for continuous cost optimization.
