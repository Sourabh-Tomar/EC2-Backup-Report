import boto3
import json
from datetime import datetime, timezone
from botocore.exceptions import ClientError

backup_client = boto3.client('backup', region_name='******') 
ec2_client = boto3.client('ec2', region_name='******') 
ses_client = boto3.client('ses', region_name='*******') 

SENDER = "*************************"  
RECIPIENT = "**********************"  

def send_email(subject, body):
    try:
        response = ses_client.send_email(
            Source=SENDER,
            Destination={
                'ToAddresses': [RECIPIENT]
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Html': {
                        'Data': body,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        print(f"Email sent! Message ID: {response['MessageId']}")
    except ClientError as e:
        print(f"Failed to send email: {e.response['Error']['Message']}")
        raise  

def lambda_handler(event, context):
    try:
        today = datetime.now(timezone.utc).date()

        result_list = []

        response = backup_client.list_backup_jobs()

        if 'BackupJobs' not in response or len(response['BackupJobs']) == 0:
            print("No backup jobs found.")
            return {
                'statusCode': 200,
                'body': json.dumps('No backup jobs found.')
            }

        for job in response['BackupJobs']:
            resource_arn = job['ResourceArn']
            backup_status = job['State']
            resource_type = job['ResourceType']
            job_status = job.get('StatusMessage', 'N/A') 
            creation_date = job['CreationDate'].date()  

            if creation_date != today:
                continue  

            if 'instance/' in resource_arn:
                resource_id = resource_arn.split("/")[-1]

                try:
                    ec2_response = ec2_client.describe_instances(InstanceIds=[resource_id])

                    if not ec2_response['Reservations']:
                        print(f"No instances found for resource ID: {resource_id}")
                        continue  

                    ec2_instance = ec2_response['Reservations'][0]['Instances'][0]

                    instance_name = 'Unnamed'
                    if 'Tags' in ec2_instance:
                        for tag in ec2_instance['Tags']:
                            if tag['Key'] == 'Name':
                                instance_name = tag['Value']
                                break

                    print(f"Instance Name: {instance_name}, Backup Status: {backup_status}")

                    result_list.append({
                        'InstanceName': instance_name,
                        'BackupStatus': backup_status,
                        'ResourceId': resource_id,
                        'ResourceType': resource_type,
                        'MessageCategory': job_status
                    })

                except ClientError as e:
                    if e.response['Error']['Code'] == 'InvalidInstanceID.NotFound':
                        print(f"Instance ID '{resource_id}' not found. It might have been terminated.")
                        continue
                    else:
                        raise


        email_body = "<h1>Backup Job Statuses</h1>"
        email_body += "<table border='1'><tr style='background-color:#0096FF;color:white;'><th>VM Name</th><th>Backup Status</th><th>Resource ID</th><th>Resource Type</th><th>Message Category</th></tr>"
        
        if result_list:
            for result in result_list:
                email_body += f"<tr><td>{result['InstanceName']}</td><td>{result['BackupStatus']}</td><td>{result['ResourceID']}</td><td>{result['ResourceType']}</td><td>{result['MessageCategory']}</td></tr>"
        else:
            email_body += "<tr><td colspan='5'>No EC2 backup jobs found for today.</td></tr>"
        
        email_body += "</table>"

        send_email(subject="EC2 Backup Job Statuses", body=email_body)

        return {
            'statusCode': 200,
            'body': json.dumps('Backup job status fetched and email sent successfully')
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error occurred: {str(e)}")
        }
