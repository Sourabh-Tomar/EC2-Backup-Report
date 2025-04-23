import boto3
import json
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# Initialize AWS clients
backup_client = boto3.client('backup', region_name='******') #Replace with your AWS region
ec2_client = boto3.client('ec2', region_name='******') #Replace with your AWS region
ses_client = boto3.client('ses', region_name='*******') #Replace with your AWS region

SENDER = "*************************"  # Replace with your verified sender email
RECIPIENT = "**********************"  # Replace with your verified recipient email

def send_email(subject, body):
    try:
        # Send the email via SES
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
        raise  # Raise the exception to capture it in the Lambda logs

def lambda_handler(event, context):
    try:
        # Get today's date in UTC
        today = datetime.now(timezone.utc).date()

        # List to store the results
        result_list = []

        # Step 1: List all backup jobs
        response = backup_client.list_backup_jobs()

        # Step 2: Check if there are any backup jobs returned
        if 'BackupJobs' not in response or len(response['BackupJobs']) == 0:
            print("No backup jobs found.")
            return {
                'statusCode': 200,
                'body': json.dumps('No backup jobs found.')
            }

        # Step 3: Iterate over each backup job
        for job in response['BackupJobs']:
            resource_arn = job['ResourceArn']
            backup_status = job['State']
            resource_type = job['ResourceType']
            job_status = job.get('StatusMessage', 'N/A')  # Get StatusMessage, or 'N/A' if it doesn't exist
            creation_date = job['CreationDate'].date()  # Get the CreationDate

            # Filter to only include today's jobs
            if creation_date != today:
                continue  # Skip jobs that are not from today

            if 'instance/' in resource_arn:
                resource_id = resource_arn.split("/")[-1]

                # Step 4: Describe the EC2 instance to get the name
                try:
                    ec2_response = ec2_client.describe_instances(InstanceIds=[resource_id])

                    if not ec2_response['Reservations']:
                        print(f"No instances found for resource ID: {resource_id}")
                        continue  # Skip to the next backup job

                    ec2_instance = ec2_response['Reservations'][0]['Instances'][0]

                    # Find the 'Name' tag
                    instance_name = 'Unnamed'
                    if 'Tags' in ec2_instance:
                        for tag in ec2_instance['Tags']:
                            if tag['Key'] == 'Name':
                                instance_name = tag['Value']
                                break

                    # Print the EC2 instance name and backup status to the Lambda console
                    print(f"Instance Name: {instance_name}, Backup Status: {backup_status}")

                    # Add the result to the list
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

        # Prepare the email content in HTML table format
        email_body = "<h1>Backup Job Statuses</h1>"
        email_body += "<table border='1'><tr style='background-color:#0096FF;color:white;'><th>VM Name</th><th>Backup Status</th><th>Resource ID</th><th>Resource Type</th><th>Message Category</th></tr>"
        
        if result_list:
            for result in result_list:
                email_body += f"<tr><td>{result['InstanceName']}</td><td>{result['BackupStatus']}</td><td>{result['ResourceId']}</td><td>{result['ResourceType']}</td><td>{result['MessageCategory']}</td></tr>"
        else:
            email_body += "<tr><td colspan='5'>No EC2 backup jobs found for today.</td></tr>"
        
        email_body += "</table>"

        # Send the email
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
