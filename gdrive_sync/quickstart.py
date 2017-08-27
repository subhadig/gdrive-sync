import argparse
from oauth2client import tools, client
import os
from oauth2client.file import Storage
import httplib2
from googleapiclient import discovery
from googleapiclient.http import MediaFileUpload

flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
SCOPES = 'https://www.googleapis.com/auth/drive'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Gdrive Sync'

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, 'gdrive-sync')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'credential.json')
    print('credential_path:' + credential_path)
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store, flags)
        print('Storing credentials to ' + credential_path)
    return credentials

def main():
    """Shows basic usage of the Google Drive API.

    Creates a Google Drive API service object and outputs the names and IDs
    for up to 10 files.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    results = service.files().list(corpora="user", fields="nextPageToken, files(id, name, modifiedTime, mimeType)").execute()
    items = results.get('files', [])
    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print('{0} ({1}) {2} {3}'.format(item['name'], item['id'], item['modifiedTime'], item['mimeType']))
#     results = service.files().list(corpora="user", pageToken=results.get('nextPageToken'),
#                                     fields="nextPageToken, files(id, name)").execute()
#     items = results.get('files', [])
#     if not items:
#         print('No files found.')
#     else:
#         for item in items:
#             print('{0} ({1})'.format(item['name'], item['id']))
#     

def update():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    response = service.files().update(fileId='0B-MN0zPlk3EOTFNQVm1RTGR2cEU', 
                                      media_body='/home/subhadip/test.txt').execute()
    print(response)

def download():
    print('==Download==')
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    response = service.files().get_media(fileId='0B-MN0zPlk3EOTFNQVm1RTGR2cEU').execute()
    print(response)
    
def create():
    print('==Create==')
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    class _Body():
        def __init__(self, parent_id):
            self.parents = [parent_id]
    response = service.files().create(body={'parents': ['0B-MN0zPlk3EOU0JVdGR4anFDd0U'], 'name': 'Rohan_onwards.pdf'},
                                       media_body='/home/subhadip/Rohan_onwards.pdf').execute()
    print(response)

if __name__ == '__main__':
    #main()
    #update()
    #download()
    create()