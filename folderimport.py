import boto3
import json
import os
import logging
import time
import argparse
from botocore.exceptions import ClientError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AWS Configuration
AwsAccountId = os.environ.get('AWS_ACCOUNT_ID', '476621446285')
AwsRegion = os.environ.get('AWS_REGION', 'us-east-1')
UniqueId = 'MigratedDEV'

def import_quicksight_bundle(asset_bundle_path):
    try:
        # Initialize QuickSight client
        quicksight = boto3.client('quicksight', region_name=AwsRegion)

        # Read the asset bundle file
        try:
            with open(asset_bundle_path, "rb") as qsFile:
                qsFileContents = qsFile.read()
            logger.info(f"Successfully read asset bundle file: {asset_bundle_path}")
        except FileNotFoundError:
            logger.error(f"Asset bundle file not found: {asset_bundle_path}")
            return False
        except Exception as e:
            logger.error(f"Error reading asset bundle file: {e}")
            return False

        # Start the import job
        logger.info(f"Starting import job: AAB-{UniqueId}")

        try:
            response = quicksight.start_asset_bundle_import_job(
                AwsAccountId=AwsAccountId,
                AssetBundleImportJobId=f'AAB-{UniqueId}',
                AssetBundleImportSource={
                    'Body': qsFileContents
                }
            )
            logger.info(f"Import job started: {response}")
        except ClientError as e:
            logger.error(f"Error starting import job: {e}")
            return False

        # Monitor the import job status
        status = 'QUEUED_FOR_IMMEDIATE_EXECUTION'
        start_time = time.time()
        timeout = 900  # 15 minutes timeout

        while status in ['QUEUED_FOR_IMMEDIATE_EXECUTION', 'IN_PROGRESS']:
            if time.time() - start_time > timeout:
                logger.error("Import job timed out")
                return False

            try:
                response = quicksight.describe_asset_bundle_import_job(
                    AwsAccountId=AwsAccountId,
                    AssetBundleImportJobId=f'AAB-{UniqueId}'
                )
                status = response['JobStatus']
                logger.info(f"Current status: {status}")

                if status == 'SUCCESSFUL':
                    logger.info("Import job completed successfully")
                    return True
                elif status == 'FAILED_ROLLBACK_IN_PROGRESS':
                    for error in response.get('Errors', []):
                        logger.error(f"Import job failed and rollback in progress: {error}")
                    return False
                elif status == 'FAILED':
                    for error in response.get('Errors', []):
                        logger.error(f"Import job failed: {error}")
                    return False

                time.sleep(5)

            except ClientError as e:
                logger.error(f"Error checking job status: {e}")
                return False

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def parse_arguments():
    parser = argparse.ArgumentParser(description='Import QuickSight asset bundle')
    parser.add_argument('--file', '-f',
                        default="./src/QuickSightAssetBundle-Modified.zip",
                        help='Path to the QuickSight asset bundle zip file')
    parser.add_argument('--account-id', '-a',
                        help='AWS Account ID (overrides environment variable)')
    parser.add_argument('--region', '-r',
                        help='AWS Region (overrides environment variable)')
    parser.add_argument('--unique-id', '-u',
                        help='Unique ID for the import job (default: MigratedDEV)')

    return parser.parse_args()

def main():
    args = parse_arguments()

    # Update global variables if provided in arguments
    global AwsAccountId, AwsRegion, UniqueId

    if args.account_id:
        AwsAccountId = args.account_id

    if args.region:
        AwsRegion = args.region

    if args.unique_id:
        UniqueId = args.unique_id

    logger.info("Starting QuickSight asset bundle import process")
    logger.info(f"Using asset bundle file: {args.file}")
    logger.info(f"AWS Account ID: {AwsAccountId}")
    logger.info(f"AWS Region: {AwsRegion}")
    logger.info(f"Import Job ID: AAB-{UniqueId}")

    if import_quicksight_bundle(args.file):
        logger.info("Asset bundle import process completed successfully")
    else:
        logger.error("Asset bundle import process failed")
        exit(1)

if __name__ == "__main__":
    main()
