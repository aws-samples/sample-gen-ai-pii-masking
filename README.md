# PII Detection and Masking Solutions

A comprehensive collection of AWS serverless solutions for detecting and masking Personally Identifiable Information (PII) using Amazon Bedrock. This repository provides both batch processing and real-time workflow solutions to handle different use cases and data volumes.

## **Available Solutions**

### 1. Batch Processing Pipeline (`/batch`)
A secure serverless pipeline for processing CSV files with dual processing capabilities:

- **Dual Processing**: Attempts Bedrock batch inference first, falls back to direct regex-based processing
- **PII Detection**: Identifies emails, phone numbers, credit cards, SSNs, and more
- **Job Tracking**: DynamoDB table tracks all processing jobs and their status
- **Security**: KMS encryption, least-privilege IAM, bucket policies
- **Monitoring**: CloudWatch logs and EventBridge scheduling

### 2. Real-time Workflow (`/Realtime`)
An automated Step Functions workflow for processing large CSV files in parallel:

- **Parallel Processing**: Divides large files into 100-row chunks for efficient processing
- **Step Functions Orchestration**: Manages workflow with error handling and retries
- **Comprehensive PII Detection**: Uses Bedrock Nova-lite model for advanced detection
- **File Integrity**: Maintains original CSV structure while masking sensitive data
- **Scalable Architecture**: Handles large files with configurable concurrency

## Architecture Overview

Both solutions provide secure, scalable PII detection with different processing approaches:

**Batch Processing**: Best for scheduled processing, large datasets, and cost optimization
**Real-time Workflow**: Best for immediate processing, complex workflows, and parallel execution

## Quick Start

Choose the solution that best fits your needs:

### For Batch Processing
```bash
cd batch
aws cloudformation create-stack \
  --stack-name pii-batch-pipeline \
  --template-body file://template.yaml \
  --parameters ParameterKey=CodeBucketName,ParameterValue=your-code-bucket \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### For Real-time Workflow
```bash
cd Realtime
aws cloudformation create-stack \
  --stack-name pii-detection-workflow \
  --template-body file://genai-pii-mask-stack.yaml \
  --parameters ParameterKey=ExistingBucketName,ParameterValue=your-bucket-name \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

## Prerequisites

- **AWS CLI** installed and configured with appropriate permissions
- **Python 3.12** or later
- **Amazon Bedrock** access enabled (us-east-1 region)
- **IAM permissions** to create CloudFormation stacks and resources

## PII Detection Capabilities

Both solutions detect and mask:
- **Email addresses** → `<PII_EMAIL>`
- **Phone numbers** → `<PII_PHONE>`
- **Credit card numbers** → `<PII_CREDIT_CARD>`
- **Social Security Numbers** → `<PII_SSN>`
- **Names and addresses** → Appropriate PII tags
- **Bank account numbers** → `<PII_BANK_ACCOUNT>`
- **Government IDs** → `<PII_GOV_ID>`

## Input CSV Format

Both solutions expect CSV files with a 'Comments' column containing text to be processed:

```csv
SurveyID,Comments
1,"My name is John Doe and my email is john@example.com"
2,"Credit card: 4111-1111-1111-1111, phone: (555) 123-4567"
```

## Testing

A sample CSV file (`sample_pii_data.csv`) is provided for testing both solutions.

## Security and Compliance

- **Encryption**: All data encrypted at rest with KMS
- **Access Control**: Least-privilege IAM policies
- **Audit Trail**: CloudWatch logs and comprehensive tracking
- **Data Retention**: Configurable TTL on processed data
- **Network Security**: VPC endpoints available (optional)

## Monitoring and Troubleshooting

### CloudWatch Logs
Monitor Lambda function execution and error handling through CloudWatch logs.

### Job Tracking
- **Batch**: DynamoDB table tracks job status and processing method
- **Real-time**: Step Functions execution history provides detailed workflow tracking

## Cost Optimization

- **Pay-per-use**: Both solutions use serverless architecture
- **Efficient Processing**: Optimized for minimal compute time
- **Resource Management**: Automatic scaling and cleanup

## Documentation

For detailed setup, usage, and troubleshooting:
- **Batch Processing**: See `/batch/README.MD`
- **Real-time Workflow**: See `/Realtime/README.md`

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

