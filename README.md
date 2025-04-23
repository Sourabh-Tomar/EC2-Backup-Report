# EC2 Backup Job Status Email Reporter

This Python script is designed to run on AWS Lambda and automatically fetch the status of EC2 backup jobs for the current day using AWS Backup. It then sends a report via Amazon SES (Simple Email Service) in the form of an HTML email.

---

## Features

- Retrieves all EC2 backup jobs created today.
- Extracts instance names using EC2 instance tags.
- Formats job details into an HTML table.
- Sends an email report using AWS SES.

---

## Prerequisites

### 1. AWS Resources
- **Lambda Function** with appropriate IAM permissions:
  - `backup:ListBackupJobs`
  - `ec2:DescribeInstances`
  - `ses:SendEmail`
- **Verified email addresses** in Amazon SES for both sender and recipient.

### 2. Python Packages
The script uses only built-in AWS SDK packages:
- `boto3`
- `botocore`
- `datetime`
- `json`

These are pre-installed in AWS Lambda Python environments.

---

## Setup Instructions

1. **Update Configuration in Script**:
   - Replace `region_name` in `boto3.client()` calls with your AWS region (e.g., `us-west-2`).
   - Replace the `SENDER` and `RECIPIENT` emails with verified addresses from SES.

2. **Deploy to AWS Lambda**:
   - Create a new Lambda function in your AWS Console.
   - Use Python 3.9+ runtime.
   - Paste the script into the Lambda editor or upload as a `.zip`.
   - Set a suitable IAM Role with required permissions.

3. **Schedule with EventBridge (Optional)**:
   - Use Amazon EventBridge to schedule the Lambda to run daily (e.g., every morning).

---

## Output

- An HTML email report with the following columns:
  - VM Name
  - Backup Status
  - Resource ID
  - Resource Type
  - Message Category (StatusMessage)

If no EC2 backup jobs were found for today, a message row will be included in the table.

---

## Notes
- The script only processes backup jobs from the **current UTC date**.
- Only jobs related to EC2 instances (`instance/` in ARN) are included.


