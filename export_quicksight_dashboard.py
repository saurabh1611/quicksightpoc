import boto3
import time
import uuid
import requests
import argparse
import os
import zipfile
import json
import tempfile
import shutil

# Configuration for the dataset ID replacement
NEW_DATASET_ID_TO_SET = "XXXXXXXXXXXXX" # This is the ID set during the modification step

def process_qs_file(downloaded_qs_path: str, output_modified_qs_path: str, new_id_to_set: str):
    """
    Unzips a .qs file, modifies dataset IDs in JSON files, and zips it back.
    """
    print(f"\nProcessing downloaded QS file: {downloaded_qs_path}")
    temp_extract_dir = tempfile.mkdtemp()
    print(f"Created temporary directory for unzipping: {temp_extract_dir}")

    try:
        print(f"Unzipping '{downloaded_qs_path}' to '{temp_extract_dir}'...")
        with zipfile.ZipFile(downloaded_qs_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)
        print("Unzipping complete.")

        possible_data_folders = ["dataset", "datasource"]
        data_folder_path = None
        for folder_name in possible_data_folders:
            current_path = os.path.join(temp_extract_dir, folder_name)
            if os.path.isdir(current_path):
                data_folder_path = current_path
                print(f"Found data definition folder: '{folder_name}' at '{data_folder_path}'")
                break
        
        modified_files_count = 0
        if data_folder_path:
            print(f"Scanning for JSON files in '{data_folder_path}' to update dataSetId to '{new_id_to_set}'...")
            for filename in os.listdir(data_folder_path):
                if filename.endswith(".json"):
                    file_path = os.path.join(data_folder_path, filename)
                    try:
                        with open(file_path, 'r+', encoding='utf-8') as f:
                            content = json.load(f)
                            if isinstance(content, dict) and "dataSetId" in content:
                                original_id = content["dataSetId"]
                                print(f"  Processing file: {filename}, Original dataSetId: {original_id}")
                                content["dataSetId"] = new_id_to_set
                                f.seek(0)
                                json.dump(content, f, indent=2)
                                f.truncate()
                                print(f"    Updated dataSetId in {filename} to {new_id_to_set}")
                                modified_files_count += 1
                            else:
                                print(f"  Skipping file: {filename} (not a dictionary or 'dataSetId' key not found).")
                    except json.JSONDecodeError:
                        print(f"  Error decoding JSON from {filename}. Skipping.")
                    except Exception as e:
                        print(f"  Error processing file {filename}: {e}")
            if modified_files_count > 0:
                print(f"Successfully modified {modified_files_count} dataset JSON file(s).")
            else:
                print(f"No dataset JSON files were modified in '{data_folder_path}'.")
        else:
            print(f"Warning: Neither 'dataset' nor 'datasource' directory found in the bundle. Cannot update dataset IDs.")
            print("Proceeding to re-zip the bundle without dataset ID modifications.")

        base_output_name = output_modified_qs_path.rsplit('.', 1)[0] 
        print(f"\nZipping modified content from '{temp_extract_dir}' to '{output_modified_qs_path}'...")
        created_zip_file = shutil.make_archive(base_name=base_output_name, format='zip', root_dir=temp_extract_dir)
        if os.path.exists(output_modified_qs_path):
            os.remove(output_modified_qs_path)
        os.rename(created_zip_file, output_modified_qs_path)
        print(f"Successfully created modified QS file: {os.path.abspath(output_modified_qs_path)}")
        return os.path.abspath(output_modified_qs_path)
    except Exception as e:
        print(f"An error occurred during QS file processing: {e}")
        return None
    finally:
        if os.path.exists(temp_extract_dir):
            print(f"Cleaning up temporary directory: {temp_extract_dir}")
            shutil.rmtree(temp_extract_dir)

def export_quicksight_dashboard_and_modify(
    source_aws_account_id: str,
    source_profile_name: str,
    dashboard_id: str,
    source_aws_region: str,
    output_file_path_base: str = None,
    new_dataset_id_to_set: str = "XXXXXXXXXXXXX"
):
    print(f"Initiating QuickSight dashboard export for Dashboard ID: {dashboard_id} from account {source_aws_account_id} in {source_aws_region}")
    
    try:
        session = boto3.Session(profile_name=source_profile_name, region_name=source_aws_region)
        quicksight_client = session.client('quicksight')
    except Exception as e:
        print(f"Error creating Boto3 session or QuickSight client for source: {e}")
        return None

    export_job_id = f"export-{dashboard_id.replace('-', '')}-{uuid.uuid4()}"
    dashboard_arn = f"arn:aws:quicksight:{source_aws_region}:{source_aws_account_id}:dashboard/{dashboard_id}"

    base_name_for_output = output_file_path_base if output_file_path_base else f"./{dashboard_id}"
    downloaded_qs_path = f"{base_name_for_output}.qs"
    modified_qs_path = f"{base_name_for_output}_modified.qs"
    
    output_dir = os.path.dirname(downloaded_qs_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    try:
        print(f"\nStarting asset bundle export job (Job ID: {export_job_id})...")
        start_export_response = quicksight_client.start_asset_bundle_export_job(
            AwsAccountId=source_aws_account_id,
            AssetBundleExportJobId=export_job_id,
            ResourceArns=[dashboard_arn],
            ExportFormat='QUICKSIGHT_JSON',
            IncludeAllDependencies=True,
        )
        print(f"Export job started successfully. ARN: {start_export_response.get('Arn')}")
    except Exception as e:
        print(f"Error starting asset bundle export job: {e}")
        return None

    print("\nPolling export job status...")
    download_url = None
    job_status = None
    max_retries = 120 
    retries = 0
    while retries < max_retries:
        try:
            describe_job_response = quicksight_client.describe_asset_bundle_export_job(
                AwsAccountId=source_aws_account_id, AssetBundleExportJobId=export_job_id )
            job_status = describe_job_response.get('JobStatus')
            print(f"Export Job status: {job_status} (Attempt {retries + 1}/{max_retries})")
            if job_status == 'SUCCESSFUL':
                download_url = describe_job_response.get('DownloadUrl')
                print("Export job SUCCEEDED.")
                break
            elif job_status in ['FAILED', 'CANCELLED']:
                print(f"Export job {job_status}.")
                if 'Errors' in describe_job_response:
                    print("Errors from export job:")
                    for error in describe_job_response['Errors']:
                        print(f"  - Type: {error.get('Type')}, Message: {error.get('Message')}, ARN: {error.get('Arn')}")
                return None
            retries += 1
            time.sleep(10)
        except Exception as e:
            print(f"Error describing export job: {e}")
            time.sleep(10)
            retries +=1 
            if retries >= max_retries:
                 print(f"Max retries reached for export job. Last status: {job_status if job_status else 'UNKNOWN'}. Aborting.")
                 return None
            continue
    
    if not download_url:
        print(f"Export job did not succeed or no download URL. Last status: {job_status if job_status else 'UNKNOWN'}")
        return None

    print(f"\nDownloading dashboard bundle to {downloaded_qs_path}...")
    try:
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        with open(downloaded_qs_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
        print(f"Dashboard bundle downloaded successfully to: {os.path.abspath(downloaded_qs_path)}")
    except Exception as e:
        print(f"Error downloading asset bundle: {e}")
        return None

    final_modified_qs_file = process_qs_file(downloaded_qs_path, modified_qs_path, new_dataset_id_to_set)
    
    if final_modified_qs_file:
        print(f"\nExport and modification stage complete. Modified QS file: {final_modified_qs_file}")
        return final_modified_qs_file
    else:
        print(f"\nProcessing of the QS file failed during export/modify stage.")
        return None

def import_quicksight_bundle(
    target_aws_account_id: str,
    target_profile: str,
    target_aws_region: str,
    bundle_file_path: str
):
    print(f"\nInitiating QuickSight bundle import to target account {target_aws_account_id} in region {target_aws_region}...")
    print(f"Bundle file: {bundle_file_path}")
    print("IMPORTANT: This is a 'simple import' without OverrideParameters. For cross-account migrations, "
          "this may lead to failures if assets (like DataSources) in the bundle refer to ARNs "
          "from the source account. Check import job errors carefully.")

    try:
        target_session = boto3.Session(profile_name=target_profile, region_name=target_aws_region)
        target_quicksight_client = target_session.client('quicksight')
    except Exception as e:
        print(f"Error creating Boto3 session for target account: {e}")
        return False

    try:
        with open(bundle_file_path, 'rb') as f:
            bundle_body = f.read()
        
        file_size_mb = len(bundle_body) / (1024 * 1024)
        print(f"Bundle file size: {file_size_mb:.2f} MB")
        if file_size_mb > 20: # AWS API direct upload limit for 'Body'
            print("Error: Bundle file size exceeds 20MB. This script currently uses direct body upload. "
                  "For larger files, consider using AWS Console import or a script that supports S3-URI based imports.")
            return False
        import_source = {'Body': bundle_body}
    except Exception as e:
        print(f"Error reading bundle file '{bundle_file_path}': {e}")
        return False

    base_bundle_name = os.path.basename(bundle_file_path).replace('.qs', '').replace('_modified', '')
    import_job_id = f"import-{base_bundle_name}-{uuid.uuid4()}"
    print(f"Generated Import Job ID: {import_job_id}")

    try:
        start_import_params = {
            'AwsAccountId': target_aws_account_id,
            'AssetBundleImportJobId': import_job_id,
            'AssetBundleImportSource': import_source
            # OverrideParameters are intentionally omitted for "simple import"
        }
        
        start_import_response = target_quicksight_client.start_asset_bundle_import_job(**start_import_params)
        print(f"Import job started successfully. ARN: {start_import_response.get('Arn')}")
    except Exception as e:
        print(f"Error starting asset bundle import job: {e}")
        return False

    print("\nPolling import job status (this may take a few minutes)...")
    max_retries = 120
    retries = 0
    final_status = "UNKNOWN"

    while retries < max_retries:
        try:
            describe_job_response = target_quicksight_client.describe_asset_bundle_import_job(
                AwsAccountId=target_aws_account_id,
                AssetBundleImportJobId=import_job_id
            )
            job_status = describe_job_response.get('JobStatus')
            final_status = job_status
            print(f"Import Job status: {job_status} (Attempt {retries + 1}/{max_retries})")

            if job_status == 'SUCCESSFUL':
                print("Import job SUCCEEDED.")
                print(f"Imported assets should now be available in account {target_aws_account_id}, region {target_aws_region}.")
                print("Please verify their functionality, especially data source connections.")
                return True
            elif job_status in ['FAILED', 'CANCELLED']:
                print(f"Import job {job_status}.")
                if 'Errors' in describe_job_response:
                    print("Errors from import job:")
                    for error in describe_job_response['Errors']:
                        error_message = f"  - Type: {error.get('Type')}, Message: {error.get('Message')}"
                        if 'ViolatedEntities' in error:
                             error_message += f", Violated Entities: {error.get('ViolatedEntities')}"
                        print(error_message)
                        if 'Errors' in error: # Nested errors
                            for sub_error in error['Errors']:
                                print(f"    - Sub-Type: {sub_error.get('Type')}, Sub-Message: {sub_error.get('Message')}")
                return False
            retries += 1
            time.sleep(10)
        except Exception as e:
            print(f"Error describing asset bundle import job: {e}")
            time.sleep(10) 
            retries +=1
            if retries >= max_retries:
                print(f"Max retries reached. Last import job status: {final_status}. Aborting.")
                return False
            continue
            
    print(f"Import job did not reach a terminal state. Last status: {final_status}.")
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export, modify, and optionally import a QuickSight dashboard.")
    
    export_group = parser.add_argument_group('Export Options')
    export_group.add_argument("--source-account-id", required=True, help="AWS Account ID of the source QuickSight environment.")
    export_group.add_argument("--source-profile", required=True, help="AWS CLI profile name for the source account.")
    export_group.add_argument("--dashboard-id", required=True, help="The ID of the QuickSight dashboard to export from source.")
    export_group.add_argument("--aws-region", required=True, help="AWS region for the SOURCE QuickSight account (e.g., 'us-east-1').")
    export_group.add_argument("--output-file-base", help="Optional. Base path and name for output files (e.g., './exports/mydash'). Defaults to './<dashboard_id>'")

    import_group = parser.add_argument_group('Import Options')
    import_group.add_argument("--perform-import", action="store_true", help="If set, attempts to import the bundle to a target account after export and modification.")
    import_group.add_argument("--target-account-id", help="Target AWS Account ID for import.")
    import_group.add_argument("--target-profile", help="AWS CLI profile for the target account.")
    import_group.add_argument("--target-aws-region", help="AWS Region for the target QuickSight account.")
    # --override-parameters-json argument removed
    
    args = parser.parse_args()

    if args.perform_import:
        if not all([args.target_account_id, args.target_profile, args.target_aws_region]):
            parser.error("--target-account-id, --target-profile, and --target-aws-region are required when --perform-import is set.")

    modified_qs_file_path = export_quicksight_dashboard_and_modify(
        source_aws_account_id=args.source_account_id,
        source_profile_name=args.source_profile,
        dashboard_id=args.dashboard_id,
        source_aws_region=args.aws_region,
        output_file_path_base=args.output_file_base,
        new_dataset_id_to_set=NEW_DATASET_ID_TO_SET
    )

    if modified_qs_file_path and args.perform_import:
        print("\n--- Starting Import Process ---")
        import_successful = import_quicksight_bundle(
            target_aws_account_id=args.target_account_id,
            target_profile=args.target_profile,
            target_aws_region=args.target_aws_region,
            bundle_file_path=modified_qs_file_path
            # No override_parameters_json_path passed
        )
        if import_successful:
            print("\n--- Import process completed successfully. Please verify assets in the target account. ---")
        else:
            print("\n--- Import process failed or did not complete. ---")
    elif not modified_qs_file_path and args.perform_import:
        print("\nSkipping import because the export/modification step failed to produce a bundle file.")
    elif modified_qs_file_path and not args.perform_import:
        print("\nExport and modification complete. Import step was not requested.")
        print(f"Final modified bundle file is at: {modified_qs_file_path}")
    else:
        print("\nExport and modification process failed. No file to import.")
