#!/bin/bash
set -e

# Configuration
STACK_NAME=${1:-pii-detection-pipeline}
ENVIRONMENT=${2:-prod}
REGION=${3:-us-west-2}
CODE_BUCKET="${STACK_NAME}-code-${ENVIRONMENT}-${REGION}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to check for required tools
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
        exit 1
    fi
    
    if ! command -v python3.12 &> /dev/null; then
        echo -e "${RED}Python 3.12 is not installed. Please install it first.${NC}"
        exit 1
    fi
    
    if ! command -v zip &> /dev/null; then
        echo -e "${RED}zip is not installed. Please install it first.${NC}"
        exit 1
    fi
}

# Function to create and configure S3 bucket
create_code_bucket() {
    echo -e "${YELLOW}Creating/checking S3 bucket for code...${NC}"
    
    if ! aws s3api head-bucket --bucket "$CODE_BUCKET" 2>/dev/null; then
        echo -e "${YELLOW}Creating bucket: $CODE_BUCKET${NC}"
        
        # Create bucket with appropriate region configuration
        if [[ $REGION == "us-east-1" ]]; then
            aws s3api create-bucket \
                --bucket "$CODE_BUCKET" \
                --region "$REGION"
        else
            aws s3api create-bucket \
                --bucket "$CODE_BUCKET" \
                --region "$REGION" \
                --create-bucket-configuration LocationConstraint="$REGION"
        fi
        
        # Enable bucket versioning
        aws s3api put-bucket-versioning \
            --bucket "$CODE_BUCKET" \
            --versioning-configuration Status=Enabled
        
        # Block public access
        aws s3api put-public-access-block \
            --bucket "$CODE_BUCKET" \
            --public-access-block-configuration \
            "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
        
        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket "$CODE_BUCKET" \
            --server-side-encryption-configuration \
            '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
    else
        echo -e "${GREEN}Bucket $CODE_BUCKET already exists${NC}"
    fi
}

# Function to set up Python virtual environment
setup_virtual_env() {
    echo -e "${YELLOW}Setting up Python virtual environment...${NC}"
    
    python3.12 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
}

# Function to build Lambda layers
build_layers() {
    echo -e "${YELLOW}Building Lambda layers...${NC}"
    
    chmod +x build-layer.sh
    ./build-layer.sh
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to build Lambda layers${NC}"
        exit 1
    fi
}

# Function to package Lambda functions
package_functions() {
    echo -e "${YELLOW}Packaging Lambda functions...${NC}"
    
    # Create deployment directories
    mkdir -p dist/processor
    mkdir -p dist/monitor
    
    # Copy source files
    cp src/processor.py dist/processor/
    cp src/monitor.py dist/monitor/
    
    # Install dependencies in the dist directories
    pip install -r requirements.txt -t dist/processor/
    pip install -r requirements.txt -t dist/monitor/
    
    # Create ZIP files
    cd dist/processor && zip -r ../../processor.zip . && cd ../..
    cd dist/monitor && zip -r ../../monitor.zip . && cd ../..
}

# Function to upload artifacts to S3
upload_artifacts() {
    echo -e "${YELLOW}Uploading artifacts to S3...${NC}"
    
    # Upload Lambda functions
    aws s3 cp processor.zip "s3://$CODE_BUCKET/lambda/processor.zip"
    aws s3 cp monitor.zip "s3://$CODE_BUCKET/lambda/monitor.zip"
    
    # Upload Lambda layers
    aws s3 cp layers/boto3-layer.zip "s3://$CODE_BUCKET/layers/boto3-layer.zip"
    aws s3 cp layers/pandas-layer.zip "s3://$CODE_BUCKET/layers/pandas-layer.zip"
}

# Function to deploy CloudFormation stack
deploy_stack() {
    echo -e "${YELLOW}Deploying CloudFormation stack...${NC}"
    
    aws cloudformation deploy \
        --template-file template.yaml \
        --stack-name "$STACK_NAME" \
        --capabilities CAPABILITY_NAMED_IAM \
        --parameter-overrides \
            Environment="$ENVIRONMENT" \
            CodeBucketName="$CODE_BUCKET" \
        --tags \
            Environment="$ENVIRONMENT" \
            Project="PII-Detection" \
            Owner="Data-Security-Team" \
        --region "$REGION"
        
    if [ $? -ne 0 ]; then
        echo -e "${RED}Stack deployment failed${NC}"
        exit 1
    fi
}

# Function to clean up temporary files
cleanup() {
    echo -e "${YELLOW}Cleaning up...${NC}"
    
    rm -rf dist
    rm -rf layers/*.zip
    rm -f *.zip
    deactivate
}

# Function to show stack outputs
show_outputs() {
    echo -e "${YELLOW}Stack outputs:${NC}"
    
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs' \
        --output table \
        --region "$REGION"
}

# Main deployment process
echo -e "${YELLOW}Starting deployment process...${NC}"
echo "Stack Name: $STACK_NAME"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "Code Bucket: $CODE_BUCKET"

# Execute deployment steps
check_prerequisites
create_code_bucket
setup_virtual_env
build_layers
package_functions
upload_artifacts
deploy_stack
cleanup
show_outputs

echo -e "${GREEN}Deployment completed successfully!${NC}"