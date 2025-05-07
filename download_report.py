import requests
import time
import argparse
import sys
import certifi
import os
import re
from datetime import datetime

def login(session, base_url, username, password):
    url = f'{base_url}/auth/identity/connect/token'
    print(f'登入 API: {url}')
    
    payload = {
        'username': username,
        'password': password,
        'grant_type': 'password',
        'scope': 'sast_rest_api',
        'client_id': 'resource_owner_client',
        'client_secret': '014DF517-39D1-4453-B7B3-9930C563627C'
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = session.post(url, data=payload, headers=headers, verify=False)
    print(f'HTTP 狀態碼: {response.status_code}')
#    print(f'回應內容: {response.text}') 登不進去再打開查看

    if response.status_code != 200:
        print('登入失敗:', response.text)
        sys.exit(1)

    token = response.json()['access_token']
    session.headers.update({'Authorization': f'Bearer {token}'})
    print('登入成功，已設置 Bearer Token')

def get_project_id(session, base_url, project_name):
    url = f'{base_url}/projects'
    response = session.get(url)
    projects = response.json()
    for project in projects:
        if project['name'].lower() == project_name.lower():
            return project['id']
    print(f'找不到專案: {project_name}')
    sys.exit(1)

def get_latest_scan_id(session, base_url, project_id):
    url = f'{base_url}/sast/scans?projectId={project_id}'
    response = session.get(url)
    scans = response.json()
    if not scans:
        print('找不到任何掃描記錄')
        sys.exit(1)
    return scans[0]['id']

def create_report(session, base_url, scan_id):
    url = f'{base_url}/reports/sastScan'
    data = {"reportType": "PDF", "scanId": scan_id}
    response = session.post(url, json=data)
    return response.json()['reportId']

def wait_for_report_ready(session, base_url, report_id):
    url = f'{base_url}/reports/sastScan/{report_id}/status'
    for _ in range(30):
        response = session.get(url)
        status = response.json()['status']['value']
        print(f'報告狀態: {status}')
        if status == 'Created':
            return
        time.sleep(5)
    print('報告產生逾時')
    sys.exit(1)

def download_report(session, base_url, report_id, output_path):
    url = f'{base_url}/reports/sastScan/{report_id}'
    response = session.get(url)
    with open(output_path, 'wb') as f:
        f.write(response.content)
    print(f'報告已儲存至: {output_path}')

def main():
    parser = argparse.ArgumentParser(description='Download CxSAST scan report.')
    parser.add_argument('--url', required=True, help='CxSAST base URL, e.g. http://cxsast.local/CxRestAPI')
    parser.add_argument('--user', required=True, help='Username')
    parser.add_argument('--password', required=True, help='Password')
    parser.add_argument('--project', required=True, help='Project name')
    parser.add_argument('--output-dir', default='.', help='Directory to save the report (default: current directory)')

    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    output_filename = f"{args.project}_{timestamp}.pdf"

    os.makedirs(args.output_dir, exist_ok=True)
    output_path = os.path.join(args.output_dir, output_filename)
    
    session = requests.Session()

    login(session, args.url, args.user, args.password)
    project_id = get_project_id(session, args.url, args.project)
    scan_id = get_latest_scan_id(session, args.url, project_id)
    report_id = create_report(session, args.url, scan_id)
    wait_for_report_ready(session, args.url, report_id)
    download_report(session, args.url, report_id, output_path)

if __name__ == '__main__':
    main()