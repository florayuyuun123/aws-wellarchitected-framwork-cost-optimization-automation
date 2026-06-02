# Troubleshooting Guide: Automated Cost Governance on AWS

This document is continuously updated with issues, errors, and resolutions encountered during the implementation and execution of this project.

## Common Issues & Resolutions

### 1. CloudFormation Deployment Failures
**Issue:** `wasteful_infrastructure.yaml` fails to deploy with a "Limit Exceeded" error.
**Cause:** The AWS account may have reached its limit for the number of VPCs, Elastic IPs, or specific EC2 instance types (like `t3.medium`) in the selected region.
**Resolution:** 
- Check the AWS Service Quotas console.
- Modify the CloudFormation template to use a different instance type (e.g., `t2.micro`) or request a quota increase.

### 2. IAM Permissions Errors in SSM Automation
**Issue:** The SSM Automation script fails with `AccessDeniedException`.
**Cause:** The IAM Role assumed by the SSM Automation Document (`AutomationServiceRole`) lacks permissions to execute `ec2:CreateSnapshot`, `ec2:DeleteVolume`, or `ec2:StopInstances`.
**Resolution:** 
- Review the `governance_setup.yaml` CloudFormation template.
- Ensure the Inline Policy attached to the IAM Role includes the necessary Boto3/API actions required by the script. Update the stack.

### 3. Missing SNS Notifications
**Issue:** The cleanup executes successfully, but no email or alert is received.
**Cause:** The SNS topic subscription was not confirmed.
**Resolution:** 
- Check the email inbox provided during the stack creation for a "AWS Notification - Subscription Confirmation" email.
- Click the "Confirm subscription" link.

### 4. Boto3 Script Runtime Errors
**Issue:** The Python script within the SSM Document throws a syntax or indentation error.
**Cause:** YAML embedding of Python scripts can be sensitive to spacing.
**Resolution:** 
- Test the Python script locally (`ssm_automation/cleanup_script.py`) before embedding.
- Ensure proper YAML indentation is maintained in `cleanup_document.yaml`.

*(More issues will be added here as the project evolves)*
