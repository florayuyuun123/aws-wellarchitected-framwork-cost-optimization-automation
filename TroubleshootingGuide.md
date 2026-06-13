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

### 10. CloudFormation Stack Deletion Fails — EBS Volume Stuck in `deleting`
**Issue:** `flo-tech-WastefulInfra` stack deletion fails with `The following resource(s) failed to delete: [UnattachedEBSVolume]`. The volume remains stuck in `deleting` state for several minutes.
**Cause:** The SSM cleanup script called `delete_volume` immediately after `create_snapshot` without waiting for the snapshot to complete. AWS internally holds the volume in `deleting` state until any in-progress snapshots tied to it are finished, causing a multi-minute delay and CloudFormation timeout.
**Resolution:** Added a snapshot waiter in both `cleanup_script.py` and `cleanup_document.yaml` to wait for the snapshot to complete before calling `delete_volume`. The waiter checks every 15 seconds for up to 10 minutes:
```python
snapshot = ec2_client.create_snapshot(VolumeId=vol_id, Description=f"Auto-snapshot {vol_id}")
waiter = ec2_client.get_waiter('snapshot_completed')
waiter.wait(SnapshotIds=[snapshot['SnapshotId']], WaiterConfig={'Delay': 15, 'MaxAttempts': 40})
ec2_client.delete_volume(VolumeId=vol_id)
```
With this fix, the volume deletes cleanly after the snapshot completes, and CloudFormation teardown succeeds without needing a `DeletionPolicy` workaround. Always run SSM automation before `delete-stack`.

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
