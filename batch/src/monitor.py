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
    Monitor Bedrock batch inference jobs and update DynamoDB status
    """
    try:
        logger.info(f"Monitor event: {json.dumps(event)}")

        # Initialize AWS clients
        bedrock = boto3.client('bedrock')
        dynamodb = boto3.resource('dynamodb')

        # Get environment variables
        table_name = os.environ['DYNAMODB_TABLE']

        # Get table reference
        table = dynamodb.Table(table_name)

        # Scan for in-progress jobs
        response = table.scan(
            FilterExpression='#status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': 'InProgress'}
        )

        jobs_checked = 0
        jobs_updated = 0

        for item in response['Items']:
            job_id = item['jobId']
            job_arn = item.get('jobArn')

            if not job_arn or item.get('method') == 'direct_processing':
                # Skip direct processing jobs
                continue

            jobs_checked += 1
            logger.info(f"Checking job: {job_id}")

            try:
                # Get job status from Bedrock
                job_response = bedrock.get_model_invocation_job(jobIdentifier=job_arn)
                job_status = job_response['status']

                logger.info(f"Job {job_id} status: {job_status}")

                if job_status in ['Completed', 'Failed', 'Stopped']:
                    # Update DynamoDB record
                    update_expression = 'SET #status = :status, completedAt = :completedAt'
                    expression_values = {
                        ':status': job_status,
                        ':completedAt': datetime.now().isoformat()
                    }

                    if job_status == 'Failed':
                        failure_reason = job_response.get('failureMessage', 'Unknown failure')
                        update_expression += ', failureReason = :failureReason'
                        expression_values[':failureReason'] = failure_reason

                    table.update_item(
                        Key={'jobId': job_id},
                        UpdateExpression=update_expression,
                        ExpressionAttributeNames={'#status': 'status'},
                        ExpressionAttributeValues=expression_values
                    )

                    jobs_updated += 1
                    logger.info(f"Updated job {job_id} to {job_status}")

            except Exception as job_error:
                logger.error(f"Error checking job {job_id}: {str(job_error)}")
                continue

        return {
            'statusCode': 200,
            'jobsChecked': jobs_checked,
            'jobsUpdated': jobs_updated,
            'message': f'Checked {jobs_checked} jobs, updated {jobs_updated}'
        }

    except Exception as e:
        logger.error(f"Monitor error: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e)
        }