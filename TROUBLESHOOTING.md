# PII Detection Solution - Troubleshooting Guide

## Common Issues and Solutions

### 1. Deployment Issues

#### CloudFormation Stack Creation Fails
**Error**: `User: arn:aws:iam::xxx:user/xxx is not authorized to perform: iam:CreateRole`

**Solution**:
```bash
# Ensure your IAM user has these permissions:
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:CreateRole",
                "iam:AttachRolePolicy",
                "iam:PassRole",
                "iam:DeleteRole",
                "iam:DetachRolePolicy",
                "lambda:*",
                "states:*",
                "s3:*",
                "cloudformation:*",
                "bedrock:*"
            ],
            "Resource": "*"
        }
    ]
}
```

#### Bucket Name Already Exists
**Error**: `Bucket name already exists`

**Solution**: Edit `deploy.sh` and change `BUCKET_NAME` to a unique value:
```bash
BUCKET_NAME="pii-detection-bucket-$(date +%Y%m%d%H%M%S)"
```

#### Bedrock Access Denied
**Error**: `AccessDeniedException: Could not resolve the foundation model from the provided model identifier`

**Solution**:
1. Go to [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock/)
2. Navigate to "Model access"
3. Request access for "Claude 3 Sonnet"
4. Wait for approval (usually immediate)

### 2. Runtime Issues

#### Step Functions Execution Fails

**Check execution details**:
```bash
# Get latest execution
aws stepfunctions list-executions \
    --state-machine-arn YOUR_STATE_MACHINE_ARN \
    --max-items 1

# Get execution details
aws stepfunctions describe-execution \
    --execution-arn EXECUTION_ARN
```

#### Lambda Function Timeouts
**Error**: `Task timed out after 300.00 seconds`

**Solution**: Increase timeout in CloudFormation template:
```yaml
PIIDetectorFunction:
  Type: AWS::Lambda::Function
  Properties:
    Timeout: 600  # Increased from 300
```

#### Bedrock Throttling
**Error**: `ThrottlingException: Too Many Requests`

**Solutions**:
1. Reduce concurrency in Step Functions:
```yaml
"MaxConcurrency": 3  # Reduced from 8
```

2. Add exponential backoff (already implemented in Lambda code)

#### Out of Memory Errors
**Error**: `Runtime exited with error: signal: killed`

**Solution**: Increase memory in CloudFormation template:
```yaml
PIIDetectorFunction:
  Properties:
    MemorySize: 2048  # Increased from 1024
```

### 3. Data Processing Issues

#### CSV Parsing Errors
**Error**: `CSV parsing failed`

**Checklist**:
- Ensure CSV has headers
- File must be UTF-8 encoded
- Must have a "Comments" column
- Check for special characters

**Fix malformed CSV**:
```python
import pandas as pd

# Read and fix CSV
df = pd.read_csv('your-file.csv', encoding='utf-8')
df.to_csv('fixed-file.csv', index=False, encoding='utf-8')
```

#### No PII Detected
**Issue**: All text remains unchanged

**Debug steps**:
1. Check CloudWatch logs for Lambda function
2. Verify Bedrock model permissions
3. Test with sample data containing obvious PII

#### Incomplete Processing
**Issue**: Some chunks missing from output

**Debug**:
```bash
# Check S3 for orphaned chunks
aws s3 ls s3://your-bucket/temp/ --recursive
aws s3 ls s3://your-bucket/processed/ --recursive

# Clean up manually if needed
aws s3 rm s3://your-bucket/temp/ --recursive
aws s3 rm s3://your-bucket/processed/ --recursive
```

### 4. Performance Issues

#### Slow Processing
**Symptoms**: Large files take too long to process

**Optimizations**:
1. Adjust chunk size in `FileProcessorFunction`:
```python
chunk_size = 50  # Reduce from 100 for complex data
# or
chunk_size = 200  # Increase for simple data
```

2. Increase concurrency (if not hitting limits):
```yaml
"MaxConcurrency": 12  # Increase from 8
```

#### High Costs
**Monitor costs with**:
```bash
# Check Bedrock usage
aws bedrock get-foundation-model-usage --region us-east-1

# Monitor Lambda costs in CloudWatch
# Check S3 storage costs
```

**Cost reduction strategies**:
1. Optimize prompts to reduce tokens
2. Use lifecycle policies for S3 cleanup
3. Right-size Lambda memory allocation

### 5. Monitoring and Debugging

#### Check Lambda Logs
```bash
# View logs for each function
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/pii-

# Get recent log events
aws logs filter-log-events \
    --log-group-name /aws/lambda/pii-detector \
    --start-time $(date -d '1 hour ago' +%s)000
```

#### Monitor Step Functions
```bash
# List recent executions
aws stepfunctions list-executions \
    --state-machine-arn YOUR_STATE_MACHINE_ARN

# Get execution history
aws stepfunctions get-execution-history \
    --execution-arn EXECUTION_ARN
```

#### Check S3 Event Notifications
```bash
# Verify bucket notifications
aws s3api get-bucket-notification-configuration \
    --bucket YOUR_BUCKET_NAME
```

### 6. Security Issues

#### Access Denied Errors
**Error**: `AccessDenied: User not authorized`

**Check IAM permissions**:
```bash
# Test S3 access
aws s3 ls s3://your-bucket-name/

# Test Bedrock access
aws bedrock list-foundation-models --region us-east-1

# Test Lambda invocation
aws lambda invoke \
    --function-name pii-detector \
    --payload '{}' \
    response.json
```

#### Encryption Issues
All data is encrypted by default. If you need custom KMS keys:
1. Create KMS key
2. Update S3 bucket encryption configuration
3. Update Lambda environment variables

### 7. Recovery Procedures

#### Clean Failed Execution
```bash
# Remove temporary files
aws s3 rm s3://your-bucket/temp/ --recursive
aws s3 rm s3://your-bucket/processed/ --recursive

# Restart processing
aws s3 cp your-file.csv s3://your-bucket/Newfile/
```

#### Reset Solution
```bash
# Delete and redeploy stack
aws cloudformation delete-stack --stack-name pii-detection-workflow
# Wait for deletion to complete, then redeploy
./deploy.sh
```

### 8. Getting Help

#### Enable Debug Logging
Add to Lambda functions:
```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

#### Contact Information
- AWS Support: For service-specific issues
- GitHub Issues: For solution improvements
- Documentation: AWS Lambda, Step Functions, Bedrock guides

#### Useful AWS CLI Commands
```bash
# Check service limits
aws service-quotas get-service-quota \
    --service-code lambda \
    --quota-code L-B99A9384

# Monitor costs
aws ce get-cost-and-usage \
    --time-period Start=2024-01-01,End=2024-01-31 \
    --granularity MONTHLY \
    --metrics BlendedCost

# List all resources
aws cloudformation describe-stack-resources \
    --stack-name pii-detection-workflow
```