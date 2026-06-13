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

### 10. CloudFormation Stack Deletion Fails — EBS Volume Not Deleted
**Issue:** `flo-tech-WastefulInfra` stack deletion fails with `The following resource(s) failed to delete: [UnattachedEBSVolume]`.
**Cause:** CloudFormation's default `DeletionPolicy` for EBS volumes is `Snapshot`, which creates a snapshot but leaves the volume itself behind, causing the stack deletion to fail.
**Resolution:**
- Add `DeletionPolicy: Delete` to the `UnattachedEBSVolume` resource in `wasteful_infrastructure.yaml` for future deployments.
- For an already-stuck stack, manually delete the volume and use `--retain-resources` to finish the stack deletion:
```bash
# Get the volume ID
aws cloudformation describe-stack-resources \
  --stack-name flo-tech-WastefulInfra \
  --query "StackResources[?ResourceType=='AWS::EC2::Volume'].PhysicalResourceId" \
  --output text --region us-east-1

# Manually delete the volume
aws ec2 delete-volume --volume-id <volume-id> --region us-east-1

# Retry stack deletion, skipping the stuck resource
aws cloudformation delete-stack \
  --stack-name flo-tech-WastefulInfra \
  --retain-resources UnattachedEBSVolume \
  --region us-east-1
```
- Confirm the volume is gone (expect `InvalidVolume.NotFound`):
```bash
aws ec2 describe-volumes --volume-ids <volume-id> --query "Volumes[*].State" --output text --region us-east-1
```

### 5. CloudFormation `EnvironmentName` Parameter Not Found
**Issue:** `aws cloudformation create-stack` fails with `Parameters: [EnvironmentName] do not exist in the template`.
**Cause:** The `wasteful_infrastructure.yaml` template had two separate `Parameters:` blocks. YAML treats duplicate keys as an override, so the second block (containing only `LatestAmiId`) silently overwrote the first (containing `EnvironmentName`).
**Resolution:** Merged both parameter definitions into a single `Parameters:` block at the top of the template.

### 6. SNS Subscription Confirmation Email Sent to Spam
**Issue:** SNS subscription remains in "Pending confirmation" status and no email is received.
**Cause:** Gmail (and other providers) may route AWS notification emails to the Spam folder.
**Resolution:**
- Search Gmail for `from:no-reply@sns.amazonaws.com` and check Spam/Promotions tabs.
- Alternatively, manually resubscribe via CLI: `aws sns subscribe --topic-arn <ARN> --protocol email --notification-endpoint <EMAIL> --region us-east-1`

### 7. SSM `create-document` Fails with "JSON not well-formed"
**Issue:** `aws ssm create-document --content file://cleanup_document.yaml` fails with `InvalidDocumentContent: JSON not well-formed`.
**Cause:** The `aws ssm create-document` command defaults to JSON format. Passing a YAML file without specifying the format causes a parse error.
**Resolution:** Add `--document-format YAML` to the command:
```bash
aws ssm create-document \
  --name "flo-tech-CostGovCleanup" \
  --document-type "Automation" \
  --document-format YAML \
  --content file://ssm_automation/cleanup_document.yaml \
  --region us-east-1
```

### 8. SSM `create-document` Fails with "python3.8 is not a supported runtime"
**Issue:** SSM Automation document creation fails with `InvalidDocumentContent: python3.8 is not a supported runtime`.
**Cause:** AWS deprecated Python 3.8 as a runtime for SSM Automation `aws:executeScript` actions.
**Resolution:** Update `Runtime: python3.8` to `Runtime: python3.11` in `cleanup_document.yaml`.

### 9. SSM Automation Execution Fails with `AccessDeniedException` on `s3:ListBuckets`
**Issue:** SSM Automation execution status shows `Failed`. The failure message in the step output reads: `AccessDeniedException` when calling `list_buckets`.
**Cause:** `s3:ListBuckets` (used by `boto3 s3_client.list_buckets()`) maps to the IAM action `s3:ListAllMyBuckets`, NOT `s3:ListBucket`. These are two completely different IAM actions. The policy in `governance_setup.yaml` was missing `s3:ListAllMyBuckets`.
**Resolution:** Add the following two actions to the IAM inline policy in `governance_setup.yaml` and redeploy the `flo-tech-Governance` stack:
```yaml
- s3:ListAllMyBuckets
- s3:GetLifecycleConfiguration
```
Then update or recreate the `flo-tech-Governance` CloudFormation stack:
```bash
aws cloudformation create-stack \
  --stack-name flo-tech-Governance \
  --template-body file://cloudformation/governance_setup.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters ParameterKey=NotificationEmail,ParameterValue=prettyflo02@gmail.com \
  --region us-east-1
```
