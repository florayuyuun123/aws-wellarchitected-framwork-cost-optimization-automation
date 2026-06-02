import boto3
import json

def cleanup_unattached_volumes(ec2_client):
    print("Scanning for unattached EBS volumes...")
    volumes = ec2_client.describe_volumes(
        Filters=[{'Name': 'status', 'Values': ['available']}]
    )['Volumes']
    
    deleted_volumes = []
    for volume in volumes:
        vol_id = volume['VolumeId']
        print(f"Found unattached volume: {vol_id}. Creating snapshot before deletion...")
        
        # Create a snapshot for safety
        snapshot = ec2_client.create_snapshot(
            VolumeId=vol_id,
            Description=f"Snapshot of unattached volume {vol_id} created by Cost Governance Automation"
        )
        print(f"Created snapshot: {snapshot['SnapshotId']}")
        
        # Delete the volume
        print(f"Deleting volume: {vol_id}")
        ec2_client.delete_volume(VolumeId=vol_id)
        deleted_volumes.append(vol_id)
        
    return deleted_volumes

def stop_idle_instances(ec2_client):
    print("Scanning for running EC2 instances with 'Idle' tag...")
    instances = ec2_client.describe_instances(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']},
            {'Name': 'tag:Status', 'Values': ['Idle']}
        ]
    )
    
    stopped_instances = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            inst_id = instance['InstanceId']
            print(f"Found idle instance: {inst_id}. Stopping it to save costs...")
            ec2_client.stop_instances(InstanceIds=[inst_id])
            stopped_instances.append(inst_id)
            
    return stopped_instances

def apply_s3_lifecycle_policies(s3_client):
    print("Scanning for inefficient S3 buckets...")
    response = s3_client.list_buckets()
    updated_buckets = []
    for bucket in response['Buckets']:
        bucket_name = bucket['Name']
        if 'inefficient-logs' in bucket_name:
            print(f"Found inefficient bucket: {bucket_name}. Applying lifecycle policy...")
            lifecycle_config = {
                'Rules': [
                    {
                        'ID': 'MoveToGlacierAndExpire',
                        'Status': 'Enabled',
                        'Filter': {'Prefix': ''},
                        'Transitions': [
                            {'Days': 30, 'StorageClass': 'GLACIER'}
                        ],
                        'Expiration': {'Days': 365}
                    }
                ]
            }
            try:
                s3_client.put_bucket_lifecycle_configuration(
                    Bucket=bucket_name,
                    LifecycleConfiguration=lifecycle_config
                )
                updated_buckets.append(bucket_name)
            except Exception as e:
                print(f"Error applying policy to {bucket_name}: {str(e)}")
    return updated_buckets

def handler(event, context):
    ec2 = boto3.client('ec2')
    s3 = boto3.client('s3')
    sns = boto3.client('sns')
    
    # Optional: Retrieve SNS Topic ARN from event if passed, or environment
    sns_topic_arn = event.get('SNSTopicArn')
    
    deleted_volumes = cleanup_unattached_volumes(ec2)
    stopped_instances = stop_idle_instances(ec2)
    updated_buckets = apply_s3_lifecycle_policies(s3)
    
    summary = {
        "DeletedVolumes": deleted_volumes,
        "StoppedInstances": stopped_instances,
        "OptimizedBuckets": updated_buckets
    }
    
    print("Cleanup Summary:", json.dumps(summary, indent=2))
    
    # Notify via SNS if provided
    if sns_topic_arn and (deleted_volumes or stopped_instances or updated_buckets):
        message = f"Cost Governance Automation Executed.\n\nSummary:\nDeleted Unattached Volumes: {deleted_volumes}\nStopped Idle Instances: {stopped_instances}\nOptimized S3 Buckets: {updated_buckets}"
        sns.publish(
            TopicArn=sns_topic_arn,
            Subject="AWS Cost Governance Alert: Automated Remediation Executed",
            Message=message
        )
        
    return summary

# Note: In a real Lambda or SSM embedded script, the handler is the entry point.
