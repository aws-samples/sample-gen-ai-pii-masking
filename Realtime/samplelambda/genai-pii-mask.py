import boto3
import pandas as pd
import io
import json
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

def obfuscate_pii(text):
    try:
        prompt = """You are a PII detection and masking system. Your task is to identify and mask personally identifiable information (PII) in input text. When you detect PII, replace it with a corresponding PII entity type tag.

Use the following masking tags:
- Credit card numbers: <PII_CREDIT_CARD>
- Names: <PII_NAME>
- Email addresses: <PII_EMAIL>
- Street/postal addresses: <PII_ADDRESS>
- Phone numbers: <PII_PHONE>
- Bank account numbers: <PII_BANK_ACCOUNT>
- Government IDs (SSN, driver's license, passport, etc): <PII_GOV_ID>
- Dates of birth: <PII_DOB>
- Geolocation coordinates: <PII_GEOLOCATION>
- Organization account numbers: <PII_ORG_ACCOUNT>
- Associated IDs (airline, car rental, etc): <PII_ASSOCIATED_ID>
- Digital signatures (IP, MAC, Device ID, etc): <PII_DIGITAL_SIG>
- Health/medical information: <PII_MEDICAL>
- Password( similaly PWD): <PII_PASSWORD> 

Guidelines:
1. Analyze the input text and identify any PII elements
2. Replace each PII element with its corresponding mask tag
3. Preserve the original text structure and formatting
4. Return only the masked text without any additional commentary
5. Process text in-place, maintaining original word order and punctuation
6. Be thorough in detecting PII across different formats and patterns
7. Handle partial or incomplete PII data conservatively
8. Maintain case sensitivity of non-PII text
9. Preserve spacing and line breaks
10. Do not add any explanations or metadata to the output

Remember: Your output should contain only the masked text, with no additional commentary, formatting, or explanations."""

        response = bedrock.converse(
            modelId='us.amazon.nova-lite-v1:0',
            messages=[{
                'role': 'user',
                'content': [{ 
                    'text': f"{prompt} + Text to analyze: {text}"
                }]
            }]
        )
        logger.info(f"Bedrock response: {response}")
        return response['output']['message']['content'][0]['text']
    except Exception as e:
        logger.error(f"Error in PII detection: {str(e)}")
        return text  # Return original text if processing fails

def lambda_handler(event, context):
    logger.info("Starting PII detection and obfuscation process")
    
    try:
        # Extract source file information
        source_bucket = event['Records'][0]['s3']['bucket']['name']
        source_key = event['Records'][0]['s3']['object']['key']
        logger.info(f"Processing file: {source_key} from bucket: {source_bucket}")
        
        # Validate file format
        if not source_key.endswith('.csv'):
            logger.error(f"Invalid file format. Expected CSV, got: {source_key}")
            return {'statusCode': 400, 'body': 'Invalid file format'}
        
        # Read PII types from configuration
        logger.info("Reading PII configuration file")
        try:
            pii_config = s3.get_object(Bucket=source_bucket, Key='config/pii_types.txt')
            pii_types = pii_config['Body'].read().decode('utf-8').splitlines()
            pii_types = [ptype.strip('* ') for ptype in pii_types if ptype.strip()]
            logger.info(f"Successfully loaded {len(pii_types)} PII types from configuration")
        except Exception as e:
            logger.error(f"Failed to read PII configuration: {str(e)}")
            return {'statusCode': 500, 'body': f'Error reading PII configuration: {str(e)}'}
        
        # Read source CSV
        logger.info("Reading source CSV file")
        try:
            obj = s3.get_object(Bucket=source_bucket, Key=source_key)
            df = pd.read_csv(io.BytesIO(obj['Body'].read()))
            logger.info(f"Successfully loaded CSV with {len(df)} rows")
        except Exception as e:
            logger.error(f"Failed to read source CSV: {str(e)}")
            return {'statusCode': 500, 'body': f'Error reading source CSV: {str(e)}'}
        
        # Process comments
        logger.info("Starting PII detection and obfuscation on comments")
        total_rows = len(df)
        processed_rows = 0

        for index, row in df.iterrows():
            processed_rows += 1
            logger.info(f"Processing row {processed_rows}/{total_rows}")
            if pd.notna(row['Comments']):
                df.loc[index, 'Comments'] = obfuscate_pii(row['Comments'])

        logger.info("Completed PII detection and obfuscation")
        
        # Save processed file
        logger.info("Saving processed file")
        try:
            target_key = source_key.replace('Newfile/', 'Newoutputfile/')
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            s3.put_object(Bucket=source_bucket, Key=target_key, Body=csv_buffer.getvalue())
            logger.info(f"Successfully saved processed file to {target_key}")
        except Exception as e:
            logger.error(f"Failed to save processed file: {str(e)}")
            return {'statusCode': 500, 'body': f'Error saving processed file: {str(e)}'}
        
        logger.info("Processing completed successfully")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Processing complete',
                'input_file': source_key,
                'output_file': target_key,
                'rows_processed': total_rows
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}")
        return {'statusCode': 500, 'body': f'Unexpected error: {str(e)}'}