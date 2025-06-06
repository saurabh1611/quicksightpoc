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
import sys
import base64 # Import base64 module

def process_qs_file(
    downloaded_qs_path: str,
    output_modified_qs_path: str,
    dashboard_replacements_map: dict,  # For specific replacements in 'dashboard' folder
    p_old_account_id: str,             # Generic Account ID old value for 'dataset' folder
    p_new_account_id: str              # Generic Account ID new value for 'dataset' folder
):
    """
    Unzips a .qs file, modifies specified content in JSON files, and zips it back.
    Modifications include:
    1. Specific string replacements in 'dashboard' folder JSON files.
    2. Global string replacement of generic Account ID in 'dataset'/'datasource' folder JSON files.
    """
    print(f"\nProcessing downloaded QS file: {downloaded_qs_path}")
    temp_extract_dir = tempfile.mkdtemp()
    print(f"Created temporary directory for unzipping: {temp_extract_dir}")

    try:
        print(f"Unzipping '{downloaded_qs_path}' to '{temp_extract_dir}'...")
        with zipfile.ZipFile(downloaded_qs_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)
        print("Unzipping complete.")

        # --- Stage 1: Process files in 'dashboard' folder for specific replacements ---
        dashboard_folder_path = os.path.join(temp_extract_dir, "dashboard")
        dashboard_files_processed_count = 0
        dashboard_string_replacements_done_count = 0

        if os.path.isdir(dashboard_folder_path):
            print(f"\nProcessing JSON files in 'dashboard' folder: {dashboard_folder_path}")
            for filename in os.listdir(dashboard_folder_path):
                if filename.endswith(".json"):
                    dashboard_files_processed_count += 1
                    file_path = os.path.join(dashboard_folder_path, filename)
                    print(f"  Processing dashboard file: {filename}")
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content_string = f.read()
                        
                        original_content_string = content_string
                        for old_id, new_id in dashboard_replacements_map.items():
                            if old_id in content_string:
                                content_string = content_string.replace(old_id, new_id)
                                print(f"    Replaced in dashboard file: '{old_id}' with '{new_id}'")
                        
                        if content_string != original_content_string:
                            dashboard_string_replacements_done_count +=1
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(content_string)
                            print(f"    Dashboard file {filename} updated with specific replacements.")
                        else:
                            print(f"    No specific dashboard replacements made in {filename}.")

                    except Exception as e:
                        print(f"  ERROR: An unexpected error occurred while processing dashboard file {filename}: {e}")
            print("\nSummary of 'dashboard' folder modifications:")
            print(f"  Dashboard JSON files scanned: {dashboard_files_processed_count}")
            print(f"  Dashboard files where specific string replacements were made: {dashboard_string_replacements_done_count}")
        else:
            print("\nWarning: 'dashboard' directory not found in the bundle. Skipping specific dashboard replacements.")


        # --- Stage 2: Process files in 'dataset' or 'datasource' folder for generic Account ID replacement ---
        possible_data_folders = ["dataset", "datasource"]
        data_folder_path = None
        for folder_name in possible_data_folders:
            current_path = os.path.join(temp_extract_dir, folder_name)
            if os.path.isdir(current_path):
                data_folder_path = current_path
                print(f"\nFound data definition folder for generic Account ID replacement: '{folder_name}' at '{data_folder_path}'")
                break

        dataset_files_scanned = 0
        account_id_replaced_in_files_count = 0
        
        if data_folder_path:
            print(f"Scanning for JSON files in '{os.path.basename(data_folder_path)}' folder to perform generic Account ID modifications...")
            for filename in os.listdir(data_folder_path):
                if filename.endswith(".json"):
                    dataset_files_scanned += 1
                    file_path = os.path.join(data_folder_path, filename)
                    print(f"  Processing dataset/datasource file for Account ID: {filename}")

                    file_had_account_id_replaced = False
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            raw_content_string = f.read()
                        modified_content_string = raw_content_string

                        if p_old_account_id and p_new_account_id and p_old_account_id in modified_content_string:
                            temp_str = modified_content_string.replace(p_old_account_id, p_new_account_id)
                            if temp_str != modified_content_string:
                                modified_content_string = temp_str
                                print(f"    Replaced generic Account ID string '{p_old_account_id}' with '{p_new_account_id}'.")
                                file_had_account_id_replaced = True
                        
                        if file_had_account_id_replaced:
                               with open(file_path, 'w', encoding='utf-8') as f:
                                   f.write(modified_content_string)
                               account_id_replaced_in_files_count += 1
                        else:
                            print(f"    No generic Account ID replacement needed or found in {filename}.")

                    except Exception as e:
                        print(f"  ERROR: An unexpected error occurred while processing {filename} for Account ID replacement: {e}")
            
            print(f"\nSummary of '{os.path.basename(data_folder_path)}' folder modifications (Account ID):")
            if dataset_files_scanned > 0:
                print(f"  Files scanned: {dataset_files_scanned}")
                print(f"  Files where generic Account ID string was replaced: {account_id_replaced_in_files_count}")
            else:
                print(f"  No JSON files found or processed in '{os.path.basename(data_folder_path)}'. This is expected if export was run with --no-include-all.")
        else:
            print(f"\nWarning: Neither 'dataset' nor 'datasource' directory found for generic Account ID replacements. This is expected if export was run with --no-include-all.")

        # --- Stage 3: Re-zip the bundle ---
        base_output_name = os.path.splitext(output_modified_qs_path)[0]
        print(f"\nZipping modified content from '{temp_extract_dir}' to '{output_modified_qs_path}'...")
        created_zip_file = shutil.make_archive(base_name=base_output_name, format='zip', root_dir=temp_extract_dir)
        final_qs_path = base_output_name + ".qs"
        if os.path.exists(final_qs_path) and final_qs_path != created_zip_file:
            os.remove(final_qs_path)
        if created_zip_file != final_qs_path:
            os.rename(created_zip_file, final_qs_path)
        else:
            final_qs_path = created_zip_file
        print(f"Successfully created modified bundle file: {os.path.abspath(final_qs_path)}")
        return os.path.abspath(final_qs_path)
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
    include_all_dependencies: bool,
    output_file_path_base: str = None,
    # This will now be Base64 encoded JSON
    dashboard_replacements_json: str = "", 
    old_account_id: str = "",
    new_account_id: str = ""
):
    print(f"Initiating QuickSight dashboard export for Dashboard ID: {dashboard_id} from account {source_aws_account_id} in {source_aws_region}")
    print(f"Include all dependencies: {include_all_dependencies}")
    print(f"Dashboard specific replacements JSON (Base64): {dashboard_replacements_json}")
    print(f"Generic Account ID replacement: OLD='{old_account_id}', NEW='{new_account_id}'")


    try:
        session_params = {"region_name": source_aws_region}
        if source_profile_name:
            session_params["profile_name"] = source_profile_name
        session = boto3.Session(**session_params)
        quicksight_client = session.client('quicksight')
    except Exception as e:
        print(f"Error creating Boto3 session or QuickSight client for source: {e}")
        return None

    export_job_id = f"export-{dashboard_id.replace('-', '')}-{uuid.uuid4()}"
    dashboard_arn = f"arn:aws:quicksight:{source_aws_region}:{source_aws_account_id}:dashboard/{dashboard_id}"

    base_name_for_output = output_file_path_base if output_file_path_base else f"./{dashboard_id.replace(':', '_').replace('/', '_')}"
    downloaded_qs_path = f"{base_name_for_output}_original.qs"
    modified_qs_path = f"{base_name_for_output}_modified.qs"

    output_dir = os.path.dirname(os.path.abspath(downloaded_qs_path))
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
            IncludeAllDependencies=include_all_dependencies,
        )
        print(f"Export job started successfully. ARN: {start_export_response.get('Arn')}")
    except Exception as e:
        print(f"Error starting asset bundle export job: {e}")
        return None

    print("\nPolling export job status...")
    download_url = None
    job_status = "UNKNOWN"
    max_retries = 120
    retries = 0
    while retries < max_retries:
        try:
            describe_job_response = quicksight_client.describe_asset_bundle_export_job(
                AwsAccountId=source_aws_account_id, AssetBundleExportJobId=export_job_id)
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
                    for error_item in describe_job_response['Errors']:
                        print(f"  - Type: {error_item.get('Type')}, Message: {error_item.get('Message')}, ARN: {error_item.get('Arn')}")
                return None
            retries += 1
            time.sleep(10)
        except Exception as e:
            print(f"Error describing export job status: {e}")
            time.sleep(10)
            retries +=1
            if retries >= max_retries:
                print(f"Max retries reached for export job. Last status: {job_status}. Aborting.")
                return None
            continue

    if not download_url:
        print(f"Export job did not succeed or no download URL was provided. Last status: {job_status}")
        return None

    print(f"\nDownloading dashboard bundle to {os.path.abspath(downloaded_qs_path)}...")
    try:
        response = requests.get(download_url, stream=True)
        response.raise_for_status()
        with open(downloaded_qs_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Dashboard bundle downloaded successfully: {os.path.abspath(downloaded_qs_path)}")
    except Exception as e:
        print(f"Error downloading asset bundle: {e}")
        return None

    # Decode the Base64 string and parse it as JSON
    dashboard_replacements_map = {}
    if dashboard_replacements_json: # Check if string is not empty
        try:
            decoded_json_bytes = base64.b64decode(dashboard_replacements_json)
            dashboard_replacements_map = json.loads(decoded_json_bytes.decode('utf-8'))
        except (base64.binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"ERROR: Failed to decode or parse dashboard_replacements_json (Base64): {e}")
            print(f"Received Base64 string was: '{dashboard_replacements_json}'")
            return None # Stop execution if parsing fails


    final_modified_qs_file = process_qs_file(
        downloaded_qs_path,
        modified_qs_path,
        dashboard_replacements_map, # Pass the dynamically determined map
        old_account_id,            # Pass the dynamically determined old account ID
        new_account_id             # Pass the dynamically determined new account ID
    )

    if final_modified_qs_file:
        print(f"\nExport and modification stage complete. Modified QS file available at: {final_modified_qs_file}")
        return final_modified_qs_file
    else:
        print("\nProcessing of the QS file failed or no modifications made during export/modify stage.")
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
          "from the source account, or if other ID conflicts occur. Check import job errors carefully.")
    if "--no-include-all" in " ".join(sys.argv).lower():
        print("Warning: If this bundle was exported with --no-include-all, ensure all dependencies "
              "(DataSources, DataSets, Themes) exist and are accessible in the target account.")


    try:
        session_params = {"region_name": target_aws_region}
        if target_profile:
            session_params["profile_name"] = target_profile
        target_session = boto3.Session(**session_params)
        target_quicksight_client = target_session.client('quicksight')
    except Exception as e:
        print(f"Error creating Boto3 session for target account: {e}")
        return False

    if not os.path.exists(bundle_file_path):
        print(f"Error: Bundle file not found at path: {bundle_file_path}")
        return False

    try:
        with open(bundle_file_path, 'rb') as f:
            bundle_body = f.read()

        file_size_mb = len(bundle_body) / (1024 * 1024)
        print(f"Bundle file size: {file_size_mb:.2f} MB")
        if file_size_mb > 40:
            print("Warning: Bundle file size is large. AWS API might have limitations for direct upload."
                  "If import fails, consider using S3 URI based import via AWS Console or an updated script.")

        import_source = {'Body': bundle_body}
    except Exception as e:
        print(f"Error reading bundle file '{bundle_file_path}': {e}")
        return False

    base_bundle_name = os.path.basename(bundle_file_path).rsplit('.', 1)[0].replace('_modified', '').replace('_original', '')
    import_job_id = f"import-{base_bundle_name}-{uuid.uuid4()}"
    print(f"Generated Import Job ID: {import_job_id}")

    try:
        start_import_params = {
            'AwsAccountId': target_aws_account_id,
            'AssetBundleImportJobId': import_job_id,
            'AssetBundleImportSource': import_source
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
                print("Please verify their functionality, especially data source connections and dataset refresh capabilities.")
                return True
            elif job_status in ['FAILED', 'CANCELLED']:
                print(f"Import job {job_status}.")
                if 'Errors' in describe_job_response:
                    print("Errors from import job:")
                    for error_item in describe_job_response['Errors']:
                        error_message = f"  - Type: {error_item.get('Type')}, Message: {error_item.get('Message')}"
                        if 'ViolatedEntities' in error_item and error_item['ViolatedEntities']:
                            error_message += f", Violated Entities: {error_item.get('ViolatedEntities')}"
                        print(error_message)
                        if 'Errors' in error_item and isinstance(error_item['Errors'], list):
                            for sub_error in error_item['Errors']:
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

    print(f"Import job did not reach a terminal state after {max_retries} retries. Last status: {final_status}.")
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export a QuickSight dashboard, modify its contents, and optionally import it to a target account.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("--export-only", action="store_true", help="Only perform export and modification. Do not import.")
    action_group.add_argument("--export-and-import", action="store_true", help="Perform export, modification, AND import to target.")
    action_group.add_argument("--import-only", action="store_true", help="Only perform import using an existing modified bundle file.")


    export_group = parser.add_argument_group('Export Options (required if not --import-only)')
    export_group.add_argument("--source-account-id", help="AWS Account ID of the source QuickSight environment.")
    export_group.add_argument("--source-profile", help="AWS CLI profile name for the source account (optional).")
    export_group.add_argument("--dashboard-id", help="The ID of the QuickSight dashboard to export from source.")
    export_group.add_argument("--source-aws-region", help="AWS region for the SOURCE QuickSight account (e.g., 'us-east-1').")
    export_group.add_argument("--output-file-base", help="Optional. Base path and name for output files (e.g., './exports/mydash'). Defaults to './<dashboard_id>' structure.")
    export_group.add_argument(
        "--no-include-all",
        action="store_false",
        dest="include_all_dependencies",
        default=True,
        help="If set, export ONLY the dashboard definition, NOT its dependencies (datasets, data sources, themes).\n"
             "This may require dependencies to exist and be accessible in the target account.\n"
             "By default, all dependencies ARE included."
    )
    # New arguments for dynamic content modification (now expects Base64 encoded)
    export_group.add_argument("--promotion-type", help="The type of promotion (e.g., 'DEV to QA', 'QA to STAGE').")
    export_group.add_argument("--dashboard-replacements-json", help="Base64 encoded JSON string containing specific dashboard ID replacements.")
    export_group.add_argument("--old-account-id-generic", help="Generic old account ID for replacement in dataset/datasource files.")
    export_group.add_argument("--new-account-id-generic", help="Generic new account ID for replacement in dataset/datasource files.")


    import_group = parser.add_argument_group('Import Options (required if not --export-only)')
    import_group.add_argument("--target-account-id", help="Target AWS Account ID for import.")
    import_group.add_argument("--target-profile", help="AWS CLI profile for the target account (optional).")
    import_group.add_argument("--target-aws-region", help="AWS Region for the target QuickSight account.")
    import_group.add_argument("--input-bundle-file", help="Path to the .qs bundle file to import (required for --import-only).")

    args = parser.parse_args()

    # --- Debugging print statements ---
    print(f"DEBUG (Python Script Start): dashboard_replacements_json argument received: {args.dashboard_replacements_json}")
    print(f"DEBUG (Python Script Start): old_account_id_generic argument received: {args.old_account_id_generic}")
    print(f"DEBUG (Python Script Start): new_account_id_generic argument received: {args.new_account_id_generic}")
    # --- End Debugging ---


    modified_qs_file_to_import = None

    # Decode the Base64 string and parse it as JSON in the main block as well
    dashboard_replacements_map_for_export = {}
    if args.dashboard_replacements_json:
        try:
            decoded_json_bytes = base64.b64decode(args.dashboard_replacements_json)
            dashboard_replacements_map_for_export = json.loads(decoded_json_bytes.decode('utf-8'))
        except (base64.binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"ERROR: Failed to decode or parse dashboard_replacements_json (Base64) in main script: {e}")
            print(f"Received Base64 string was: '{args.dashboard_replacements_json}'")
            sys.exit(1) # Exit if cannot parse this crucial input


    if args.export_only or args.export_and_import:
        if not all([args.source_account_id, args.dashboard_id, args.source_aws_region]):
            parser.error("--source-account-id, --dashboard-id, and --source-aws-region are required for export actions.")
        print("--- Starting Export and Modification Process ---")
        modified_qs_file_to_import = export_quicksight_dashboard_and_modify(
            source_aws_account_id=args.source_account_id,
            source_profile_name=args.source_profile,
            dashboard_id=args.dashboard_id,
            source_aws_region=args.source_aws_region,
            include_all_dependencies=args.include_all_dependencies,
            output_file_path_base=args.output_file_base,
            # Pass the Base64 encoded string to the function
            dashboard_replacements_json=args.dashboard_replacements_json,
            old_account_id=args.old_account_id_generic,
            new_account_id=args.new_account_id_generic
        )
        if not modified_qs_file_to_import:
            print("\nExport and modification process failed or did not produce a file. Aborting.")
            sys.exit(1)
        if args.export_only:
            print("\n--- Export and modification complete. Import step was not requested. ---")
            print(f"Modified bundle file is available at: {modified_qs_file_to_import}")
            sys.exit(0)

    if args.import_only:
        if not args.input_bundle_file:
            parser.error("--input-bundle-file is required when using --import-only.")
        if not os.path.exists(args.input_bundle_file):
            print(f"Error: Input bundle file for import not found: {args.input_bundle_file}")
            sys.exit(1)
        modified_qs_file_to_import = os.path.abspath(args.input_bundle_file)
        print(f"--- Preparing for Import-Only using: {modified_qs_file_to_import} ---")


    if args.export_and_import or args.import_only:
        if not all([args.target_account_id, args.target_aws_region]):
            parser.error("--target-account-id and --target-aws-region are required for import actions.")
        if not modified_qs_file_to_import:
            print("\nError: No bundle file specified or generated for import. Aborting.")
            sys.exit(1)

        print("\n--- Starting Import Process ---")
        import_successful = import_quicksight_bundle(
            target_aws_account_id=args.target_account_id,
            target_profile=args.target_profile,
            target_aws_region=args.target_aws_region,
            bundle_file_path=modified_qs_file_to_import
        )
        if import_successful:
            print("\n--- Import process completed successfully. Please verify assets in the target QuickSight account. ---")
        else:
            print("\n--- Import process failed or did not complete. Review logs for details. ---")
            sys.exit(1)
    
    print("\nScript execution finished.")
