import os
import time
import json

import msal
import requests
import pandas as pd


PBI_TENANT_NAME = os.getenv('PBI_TENANT_NAME')
PBI_ADMIN_API_CLIENT_ID = os.getenv('PBI_ADMIN_API_CLIENT_ID')
PBI_ADMIN_API_SECRET = os.getenv('PBI_ADMIN_API_SECRET')

PBI_AUTHORITY = f'https://login.microsoftonline.com/{PBI_TENANT_NAME}'
PBI_SCOPES = ['https://analysis.windows.net/powerbi/api/.default']

TENANT_DIRECTOY = f'./{PBI_TENANT_NAME}'

WORKSPACES_PER_CHUNK = 100
SCAN_TIMEOUT = 30
MAX_SCAN_STATUS_POLL = 10


def get_access_token():
    '''Returns an AAD token using MSAL'''

    response = None
    try:
        clientapp = msal.ConfidentialClientApplication(
            PBI_ADMIN_API_CLIENT_ID, authority=PBI_AUTHORITY, client_credential=PBI_ADMIN_API_SECRET)
        response = clientapp.acquire_token_silent(PBI_SCOPES, account=None)
        if not response:
            response = clientapp.acquire_token_for_client(scopes=PBI_SCOPES)

        try:
            return response['access_token']
        except KeyError:
            raise Exception(response['error_description'])

    except Exception as ex:
        raise Exception('Error retrieving Access token\n' + str(ex))


def scan_worspaces(access_token, excludePersonalWorkspaces=True):
    '''Gets a list of workspace IDs in the organization'''

    api_url = f'https://api.powerbi.com/v1.0/myorg/admin/workspaces/modified?excludePersonalWorkspaces={excludePersonalWorkspaces}'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + access_token
    }

    r = requests.get(api_url, headers=headers)

    r.raise_for_status()
    r.encoding = 'utf-8-sig'
    return r.json()


def get_workspace_info(access_token, workspaces):
    '''Initiate a call to receive metadata for the requested list of workspaces'''

    api_url = f'https://api.powerbi.com/v1.0/myorg/admin/workspaces/getInfo'
    api_url += '?datasetExpressions=True&datasetSchema=True&datasourceDetails=True&getArtifactUsers=True&lineage=True'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + access_token
    }

    r = requests.post(
        api_url,
        headers=headers,
        json={
            'workspaces': workspaces
        },
    )

    r.raise_for_status()
    r.encoding = 'utf-8-sig'
    return r.headers.get('location')


def get_scan_status(access_token, api_url):
    '''Gets scan status for the specified scan.'''

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + access_token
    }

    r = requests.get(api_url, headers=headers)

    r.raise_for_status()
    response_data = r.json()
    response_data['location'] = r.headers.get('location')
    return response_data


def get_scan_result(access_token, api_url):
    '''Gets scan result for the specified scan (should be called only after getting status Succeeded in the scan status API). 
    Scan result will be available for up to 24 hours.'''

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + access_token
    }

    r = requests.get(api_url, headers=headers)

    r.raise_for_status()
    r.encoding = 'utf-8-sig'
    return r.json()


def get_all_scan_results(access_token, workspaces):
    ''' Given the list of IDs for all workspaces, divide the list in chunks of WORKSPACES_PER_CHUNK items, and for each chunck call the API to trigger a scan
    of the workspaces. Keep polling the API, every SCAN_TIMEOUT seconds until the scan finished or until the limit of MAX_SCAN_STATUS_POLL. If the scan finiched,
    call again the API to get the scan results for the workspaces in the chunck. And start again with a new chunk, until all workspaces are scanned.

    Returns a dictionary with the key 'workspaces' and as value with the list of data for each workspace.
    '''
    scan_results = {'workspaces': []}

    ws_len = len(workspaces)
    ws_index = 0
    print(f'Workspaces to scan: {ws_len}')
    while ws_index < ws_len:
        ws_index_end = ws_index + WORKSPACES_PER_CHUNK
        print(f'Scanning workspaces {ws_index} to {ws_index_end}')
        workspaces_ids = [ws['Id'] for ws in workspaces[ws_index:ws_index_end]]
        ws_index = ws_index_end
        scan_api_url = get_workspace_info(access_token, workspaces_ids)

        finish_poll = False
        poll_index = 0
        status_response = None
        while not finish_poll and poll_index < MAX_SCAN_STATUS_POLL:
            print(f'Waiting {SCAN_TIMEOUT} seconds')
            time.sleep(SCAN_TIMEOUT)
            status_response = get_scan_status(access_token, scan_api_url)
            finish_poll = status_response['status'] == 'Succeeded'
            poll_index += 1

        if status_response is not None:
            scan_results_partial = get_scan_result(access_token, status_response['location'])
            scan_results['workspaces'].extend(
                scan_results_partial['workspaces'])

        return scan_results


def save_scan_results_to_json(scan_results):
    '''Save the results of the scan of the workspaces to JSON files.
    Creates a JSON file with all the results, with the name {PBI_TENANT_NAME}_workspaces.json
    For each workspace, create a JSON file with the data for that workspace, with the name {PBI_TENANT_NAME}_workspace_{ws_name}.json
    '''
    create_tenant_directory_if_not_exists()

    json_file_name = f'{TENANT_DIRECTOY}/{PBI_TENANT_NAME}_workspaces.json'
    print(f'Saving the scan results to {json_file_name}')
    with open(json_file_name, 'w') as json_file:
        json.dump(scan_results, json_file)

    for ws_data in scan_results['workspaces']:
        ws_name = ws_data['name']
        json_file_name = f'{TENANT_DIRECTOY}/{PBI_TENANT_NAME}_workspace_{ws_name}.json'
        print(f'Saving the scan results to {json_file_name}')
        with open(json_file_name, 'w') as json_file:
            json.dump(ws_data, json_file)


def load_scan_result_to_data_frames(scan_results):
    '''Loads the scan results into separated DataFrames for worspaces, reports, dashboards, datasets, dataflows, etc.
    Returns a dictionary where the keys are the names of the dataframes and the values are the DataFrames.
    '''

    data_frames = {}

    df_workspaces = pd.json_normalize(scan_results, record_path=['workspaces'])
    data_frames['workspaces'] = df_workspaces.drop(
        columns=['reports', 'dashboards', 'datasets', 'dataflows'])

    data_frames['reports'] = pd.json_normalize(scan_results['workspaces'], record_path=[
                                               'reports'], record_prefix='report.', meta=['id', 'name'], meta_prefix='workspace.')

    data_frames['dashboards'] = pd.json_normalize(scan_results['workspaces'], record_path=[
                                                  'dashboards'], record_prefix='dashboard.', meta=['id', 'name'], meta_prefix='workspace.')

    data_frames['datasets'] = pd.json_normalize(scan_results['workspaces'], record_path=[
                                                'datasets'], record_prefix='dataset.', meta=['id', 'name'], meta_prefix='workspace.')

    data_frames['dataflows'] = pd.json_normalize(scan_results['workspaces'], record_path=[
                                                 'dataflows'], record_prefix='dataflow.', meta=['id', 'name'], meta_prefix='workspace.')

    return data_frames


def save_data_frames_to_csv(data_frames):
    '''Save the scan results loaded in DatFrames to CSV files.'''

    create_tenant_directory_if_not_exists()
    for df_name in data_frames.keys():
        df = data_frames[df_name]
        csv_file_name = f'{TENANT_DIRECTOY}/{PBI_TENANT_NAME}_{df_name}.csv'
        print(f'Saving the scan results to {csv_file_name}')
        df.to_csv(csv_file_name, header=True, index=False)


def create_tenant_directory_if_not_exists():
    '''Create the directory TENANT_DIRECTOY, to store the files for a tenant.'''
    if not os.path.exists(TENANT_DIRECTOY):
        os.makedirs(TENANT_DIRECTOY)


access_token = get_access_token()

workspaces = scan_worspaces(access_token)
scan_results = get_all_scan_results(access_token, workspaces)

save_scan_results_to_json(scan_results)

data_frames = load_scan_result_to_data_frames(scan_results)
save_data_frames_to_csv(data_frames)
