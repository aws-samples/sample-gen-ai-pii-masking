# PII Detection Pipeline - Batch Processing

A secure serverless pipeline for detecting and masking Personally Identifiable Information (PII) using Amazon Bedrock and direct processing for CSV files.

## ✅ **Working Solution**

This batch processing solution successfully detects and masks PII data in CSV files with the following features:

- **Dual Processing**: Attempts Bedrock batch inference first, falls back to direct regex-based processing
- **PII Detection**: Identifies emails, phone numbers, credit cards, SSNs, and more
- **Job Tracking**: DynamoDB table tracks all processing jobs and their status
- **Security**: KMS encryption, least-privilege IAM, bucket policies
- **Monitoring**: CloudWatch logs and EventBridge scheduling

## Architecture

**Core Components:**
- **S3 Buckets**: Input, output, and logging buckets with encryption
- **Lambda Functions**: Processor and monitor functions with dependency layers
- **DynamoDB**: Job tracking table with TTL and GSI indexes
- **EventBridge**: Automatic triggering and monitoring scheduling
- **KMS**: Data encryption keys for buckets and queues
- **SQS**: Dead letter queues for error handling

**Data Flow:**
1. CSV files uploaded to input bucket trigger EventBridge events
2. Processor Lambda attempts Bedrock batch job creation
3. If Bedrock unavailable, falls back to direct regex-based PII masking
4. Results stored in output bucket with job tracking in DynamoDB
5. Monitor Lambda checks batch job status every 15 minutes

## Prerequisites

- **AWS CLI** installed and configured with appropriate permissions
- **Python 3.12** or later
- **Amazon Bedrock** access enabled (us-east-1 region)
- **IAM permissions** to create CloudFormation stacks and resources

## Quick Deployment

### Option 1: Simplified Deployment (Recommended)

```bash
# 1. Deploy CloudFormation template directly
aws cloudformation create-stack \
  --stack-name pii-batch-pipeline \
  --template-body file://template.yaml \
  --parameters ParameterKey=CodeBucketName,ParameterValue=your-code-bucket \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# 2. Create a simple Lambda layer with dependencies
python3.12 -m venv layer_env
source layer_env/bin/activate
pip install boto3 pandas
mkdir -p layer/python
pip install boto3 pandas --target layer/python
cd layer && zip -r ../deps-layer.zip .

# 3. Upload layer and update functions
aws s3 cp deps-layer.zip s3://your-code-bucket/layers/
aws lambda publish-layer-version \
  --layer-name pii-deps \
  --content S3Bucket=your-code-bucket,S3Key=layers/deps-layer.zip \
  --compatible-runtimes python3.12 \
  --region us-east-1

# 4. Update Lambda functions to use the layer
aws lambda update-function-configuration \
  --function-name [processor-function-name] \
  --layers arn:aws:lambda:us-east-1:YOUR-ACCOUNT:layer:pii-deps:1
```

### Option 2: Full Deployment Script

```bash
# Run the full deployment script
chmod +x deploy.sh
./deploy.sh pii-batch-pipeline prod us-east-1
```

## Usage

### Input CSV Format
The input CSV file should contain the following columns:
- `SurveyID`: Unique identifier for each record
- `Comments`: Text content to be processed for PII

Example:
```csv
SurveyID,Comments
1,"My name is John Doe and my email is john@example.com"
2,"Credit card: 4111-1111-1111-1111, phone: (555) 123-4567"
```

### Processing Files

1. **Upload CSV files to the input bucket:**
```bash
aws s3 cp your-file.csv s3://[stack-name]-batch-input-[env]-[region]/
```

2. **Monitor processing status:**
```bash
# Check DynamoDB for job status
aws dynamodb scan --table-name [stack-name]-job-tracking-[env]

# Check CloudWatch logs
aws logs tail /aws/lambda/[stack-name]-ProcessorFunction-*
```

3. **Download processed results:**
```bash
aws s3 cp s3://[stack-name]-batch-output-[env]-[region]/processed-your-file.csv ./
```

### PII Detection Results

**Supported PII Types:**
- **Email addresses** → `<PII_EMAIL>`
- **Phone numbers** → `<PII_PHONE>`
- **Credit card numbers** → `<PII_CREDIT_CARD>`
- **Social Security Numbers** → `<PII_SSN>`

**Example Output:**
```csv
SurveyID,Comments
1,"My name is John Doe and my email is <PII_EMAIL>"
2,"Credit card: <PII_CREDIT_CARD>, phone: <PII_PHONE>"
```

## Testing with Sample Data

A sample CSV file is provided for testing:

```bash
# Use the provided sample file
aws s3 cp sample_pii_data.csv s3://[input-bucket]/sample_pii_data.csv

# Check results after processing
aws s3 cp s3://[output-bucket]/processed-sample_pii_data.csv ./
```

## Monitoring and Troubleshooting

### CloudWatch Logs
- **Processor Function**: `/aws/lambda/[stack-name]-ProcessorFunction-*`
- **Monitor Function**: `/aws/lambda/[stack-name]-MonitorFunction-*`

### DynamoDB Tracking
Jobs are tracked in the DynamoDB table with the following attributes:
- `jobId`: Unique job identifier
- `status`: Current job status (InProgress, Completed, Failed)
- `sourceFile`: Original file name
- `outputKey`: Processed file location
- `method`: Processing method used (bedrock_batch or direct_processing)
- `createdAt`: Job creation timestamp
- `completedAt`: Job completion timestamp

### Common Issues
1. **Import Errors**: Ensure Lambda layers are properly attached
2. **Permission Errors**: Verify IAM roles have necessary Bedrock/S3 permissions
3. **File Format**: Ensure CSV contains required 'Comments' column
4. **Bedrock Quotas**: Monitor Bedrock service quotas and limits

## Security and Compliance

- **Encryption**: All data encrypted at rest with KMS
- **Access Control**: Least-privilege IAM policies
- **Audit Trail**: CloudWatch logs and DynamoDB tracking
- **Data Retention**: Configurable TTL on processed data
- **Network Security**: VPC endpoints available (optional)

## Cost Optimization

- **DynamoDB**: Pay-per-request pricing
- **Lambda**: Reserved concurrency limits
- **S3**: Lifecycle policies for automatic cleanup
- **Layer Optimization**: Minimal dependency footprint

## Support and Documentation

For issues and questions:
1. Check CloudWatch logs for error messages
2. Verify DynamoDB job tracking entries
3. Review IAM permissions and Bedrock quotas
4. Test with sample data first

## Clean Up

To remove all resources:
```bash
aws cloudformation delete-stack --stack-name [stack-name] --region [region]
```