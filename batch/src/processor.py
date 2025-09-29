import json
import boto3
import logging
import os
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Simple PII processor that processes CSV files and creates Bedrock batch jobs
    """
    try:
        logger.info(f"Event received: {json.dumps(event)}")

        # Initialize AWS clients
        s3 = boto3.client('s3')
        bedrock = boto3.client('bedrock')
        dynamodb = boto3.resource('dynamodb')

        # Get environment variables
        input_bucket = os.environ['INPUT_BUCKET']
        output_bucket = os.environ['OUTPUT_BUCKET']
        table_name = os.environ['DYNAMODB_TABLE']
        bedrock_role_arn = os.environ['BEDROCK_ROLE_ARN']

        # Get table reference
        table = dynamodb.Table(table_name)

        # Parse S3 event
        if 'Records' in event and event['Records']:
            # S3 event
            record = event['Records'][0]
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
        else:
            # Manual invocation
            bucket = event.get('bucket', input_bucket)
            key = event.get('key', 'sample_pii_data.csv')

        logger.info(f"Processing file: s3://{bucket}/{key}")

        # Create unique job ID
        job_id = f"pii-job-{int(datetime.now().timestamp())}"

        # Create input S3 URI
        input_uri = f"s3://{bucket}/{key}"

        # Create output S3 URI
        output_key = f"processed-{key}"
        output_uri = f"s3://{output_bucket}/{output_key}"

        # Simple PII detection prompt
        prompt = """You are a PII detection and masking system. Analyze the input CSV data and replace any personally identifiable information with appropriate tags:
        - Names: <PII_NAME>
        - Email addresses: <PII_EMAIL>
        - Phone numbers: <PII_PHONE>
        - Addresses: <PII_ADDRESS>
        - Credit card numbers: <PII_CREDIT_CARD>
        - SSN: <PII_SSN>
        - Other sensitive data: <PII_SENSITIVE>

        Keep the CSV structure intact and only mask the sensitive information."""

        # Create batch inference job
        try:
            response = bedrock.create_model_invocation_job(
                jobName=job_id,
                roleArn=bedrock_role_arn,
                modelId="anthropic.claude-3-haiku-20240307-v1:0",
                inputDataConfig={
                    's3InputDataConfig': {
                        's3Uri': input_uri
                    }
                },
                outputDataConfig={
                    's3OutputDataConfig': {
                        's3Uri': output_uri
                    }
                },
                timeoutDurationInHours=24
            )

            job_arn = response['jobArn']
            logger.info(f"Created batch job: {job_arn}")

            # Store job info in DynamoDB
            table.put_item(
                Item={
                    'jobId': job_id,
                    'jobArn': job_arn,
                    'status': 'InProgress',
                    'sourceFile': key,
                    'inputBucket': bucket,
                    'outputBucket': output_bucket,
                    'outputKey': output_key,
                    'createdAt': datetime.now().isoformat(),
                    'ttl': int(datetime.now().timestamp()) + (30 * 24 * 60 * 60)  # 30 days TTL
                }
            )

            return {
                'statusCode': 200,
                'jobId': job_id,
                'jobArn': job_arn,
                'message': f'Successfully created batch job for {key}'
            }

        except Exception as bedrock_error:
            logger.warning(f"Bedrock batch job creation failed, falling back to direct processing: {str(bedrock_error)}")

            # Fall back to direct processing for small files
            try:
                # Read the CSV file
                response = s3.get_object(Bucket=bucket, Key=key)
                csv_content = response['Body'].read().decode('utf-8')

                logger.info(f"Processing {len(csv_content)} characters directly")

                # Simple PII masking (basic implementation)
                processed_content = csv_content

                # Basic patterns for demo (in production, use more sophisticated methods)
                import re

                # Email pattern
                processed_content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '<PII_EMAIL>', processed_content)

                # Phone pattern
                processed_content = re.sub(r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', '<PII_PHONE>', processed_content)

                # Credit card pattern (basic)
                processed_content = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '<PII_CREDIT_CARD>', processed_content)

                # SSN pattern
                processed_content = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '<PII_SSN>', processed_content)

                # Save processed file
                s3.put_object(
                    Bucket=output_bucket,
                    Key=output_key,
                    Body=processed_content,
                    ContentType='text/csv'
                )

                # Update DynamoDB
                table.put_item(
                    Item={
                        'jobId': job_id,
                        'status': 'Completed',
                        'sourceFile': key,
                        'inputBucket': bucket,
                        'outputBucket': output_bucket,
                        'outputKey': output_key,
                        'createdAt': datetime.now().isoformat(),
                        'completedAt': datetime.now().isoformat(),
                        'method': 'direct_processing',
                        'ttl': int(datetime.now().timestamp()) + (30 * 24 * 60 * 60)
                    }
                )

                return {
                    'statusCode': 200,
                    'jobId': job_id,
                    'method': 'direct_processing',
                    'outputFile': f's3://{output_bucket}/{output_key}',
                    'message': f'Successfully processed {key} directly'
                }

            except Exception as direct_error:
                logger.error(f"Direct processing failed: {str(direct_error)}")
                return {
                    'statusCode': 500,
                    'error': f'Both Bedrock and direct processing failed: {str(direct_error)}'
                }

    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e)
        }