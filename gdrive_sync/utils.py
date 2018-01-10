import os
import logging
import shutil

from gdrive_sync import configs
import json
from pyrfc3339 import parse, generate
from datetime import datetime
from oauth2client import file
from oauth2client import tools, client
from os import path
import httplib2
from googleapiclient import discovery
import magic

_user_settings_template = {'synced_dirs': {}}


class _Flags:
    logging_level = configs.get_config('LOGGING', 'log_level')
    noauth_local_webserver = False
    auth_host_port = [8080, 8090]
    auth_host_name = 'localhost'


def get_gdrive_sync_home():
    """
    Returns the gdrive-sync config directory for user.
    If the directory does not exists, then creates it.
    Returns: 'A String' representing the path to ~/.gdrive-sync
    """
    home_dir = os.path.expanduser('~')
    gdrive_sync_home_dir = os.path.join(home_dir, '.gdrive-sync')
    if not os.path.exists(gdrive_sync_home_dir):
        os.makedirs(gdrive_sync_home_dir)
    return gdrive_sync_home_dir


def create_logger(name):
    """
    Creates a logger with the input name and configurations from config.ini
    """
    logger = logging.getLogger(name)
    logger.setLevel(configs.get_config('LOGGING', 'log_level'))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(get_gdrive_sync_home() + '/gdrive-sync.log')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    if configs.get_configs().getboolean('LOGGING', 'console_logging'):
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger


def get_user_settings():
    """
    Gets the user settings
    """
    settings_path = os.path.join(get_gdrive_sync_home(), 'settings.json')
    if not os.path.exists(settings_path):
        store_user_settings(_user_settings_template)
    with open(settings_path, mode='r', encoding='utf-8') as _file:
        return json.load(_file)


def store_user_settings(settings):
    """
    Stores the settings object to file
    """
    settings_path = os.path.join(get_gdrive_sync_home(), 'settings.json')
    with open(settings_path, mode='w', encoding='utf-8') as _file:
        json.dump(settings, _file)


def list_drive_files(service, fields, query=None, next_page_token=None):
    """
    Gets the results from google drive with the input parameters
    """
    return service.files().list(q=query, corpora="user", fields=fields, pageToken=next_page_token).execute()


def list_files_under_local_dir(dir_path):
    """
    Lists the files as os.DirEntry under a dir in local filesystem.
    If the file is a dir, it creates a map for that entry where the key is
    the os.DirEntry for that dir and the value is the list of files under
    that dir.
    :return Generator of os.DirEntry and dict if file is dir
    """
    files = os.scandir(path=dir_path)
    for each in files:
        if each.is_dir():
            yield {each: list_files_under_local_dir(each.path)}
        else:
            yield each


def convert_rfc3339_time_to_epoch(timestamp):  # TODO: Modify test
    """
    Converts rfc3339 time to epoch timestamps
    Args:
        timestamp: 'A string' in rfc3339 format
    Returns:
        Integer, the converted epoch timestamp
    """
    return int(parse(timestamp=timestamp).timestamp())


def convert_epoch_time_to_rfc3339(timestamp):
    """
    Converts epoch timestamps time to rfc3339
    Args:
        timestamp: Float, unix epoch timestamp
    Returns:
        A string in rfc3339 format
    """
    return generate(datetime.utcfromtimestamp(timestamp), accept_naive=True)


def overwrite_remote_file_with_local(service, remote_file_id, local_file_path):
    """
    Overwrites the remote file with the local file.
    Args:
        service: A googleapiclient.discovery.Resource object
        remote_file_id: 'A String' that represents path the local file
        local_file_path: A os.DirEntry object that represents the local file
    """
    return service.files().update(fileId=remote_file_id,
                                  media_body=local_file_path,
                                  media_mime_type=magic.from_file(local_file_path, True)).execute()


def copy_remote_file_to_local(service, local_file_path, remote_file_id):
    """
    Copies the remote file to local.
    Args:
        service: A googleapiclient.discovery.Resource object
        local_file_path: 'A String' that represents path the local file
        remote_file_id: 'A String' that represents id for the file object from google drive
    """
    remote_content = service.files().get_media(fileId=remote_file_id).execute()
    with open(local_file_path, 'bw') as _file:
        _file.write(remote_content)


def copy_local_file_to_remote(local_file_path, remote_parent_dir_id, service=None):
    """
    Copies the local file under remote_parent_dir
    Args:
        service: A googleapiclient.discovery.Resource object
        local_file_path: A String path of the local file
        remote_parent_dir_id: 'A String' that represents id for the file object from google drive
    Returns:
        'A String' ID of the created google drive file
    """
    return check_and_get_service(service).files().create(body={'parents': [remote_parent_dir_id],
                                                               'name': os.path.basename(local_file_path)},
                                                         media_body=local_file_path,
                                                         media_mime_type=magic.from_file(local_file_path,
                                                                                         True)).execute()['id']


def create_remote_dir(name, parent_dir, service=None):
    """
    Creates a dir at remote.
    :param name: remote dir name
    :param parent_dir: remote parent dir id
    :param service: A googleapiclient.discovery.Resource object
    :return: the id of the created remote dir
    """
    return check_and_get_service(service).files().create(body={'parents': [parent_dir],
                                                               'name': name,
                                                               'mimeType': 'application/vnd.google-apps.folder'})\
        .execute()['id']


def get_remote_files_from_dir(service, parent_dir_id, next_page_token=None):
    """
    Gets the remote file information from remote, returns file with
    id, name, modifiedTime, mimeType fields.
    Args:
        service: A googleapiclient.discovery.Resource object
        parent_dir_id: 'A String' representing the id of the parent dir of the remote files
        next_page_token: 'A String' token to the google drive next page where the search will start from
    Results:
        A generator of files dir object
    """
    results = list_drive_files(service,
                               'nextPageToken, files(id, name, modifiedTime, mimeType)',
                               query="'{}' in parents and trashed = false".format(parent_dir_id),
                               next_page_token=next_page_token)
    if 'nextPageToken' in results:
        yield from get_remote_files_from_dir(service, parent_dir_id, results['nextPageToken'])

    yield from results['files']


def list_remote_files_from_dir(service, parent_dir_id):
    """
    Gets the remote file and directory information from remote recursively. If a file is a dir,
    it will have the generator of the child files and dirs as 'children'.

    :param service: A googleapiclient.discovery.Resource object
    :param parent_dir_id: 'A String' representing the id of the parent dir of the remote files
    :return: A generator of files and dir object
    """
    for each in get_remote_files_from_dir(service, parent_dir_id):

        if each['mimeType'] == 'application/vnd.google-apps.folder':
            each['children'] = list_remote_files_from_dir(service, each['id'])

        yield each


def get_remote_dir(service, parent_dir_id, dir_list):
    """
    Gets the remote dir id from drive.
    remote_dir_path path format: /parent_dir/child_dir
    Args:
        service: A googleapiclient.discovery.Resource object
        parent_dir_id: 'A String' representing the id of the parent dir of the remote files
        dir_list: A list of String, contains the path from parent dir to child dir
                Example: /root/home/user will be represented as ['root', 'home', 'user']
    Returns:
        A dict of below form:
            {
                'id': 'A String' id of the directory from google drive
                'modifiedTime': 'A string' date in rfc3339 format
            }

    """
    results = list_drive_files(service, "nextPageToken, files(id, modifiedTime)",
                               query="'{}' in parents and name = '{}'".format(parent_dir_id, dir_list[0]))
    this_dir_id = results['files'][0]['id']
    if len(dir_list) == 1:
        return results['files'][0]
    else:
        return get_remote_dir(service, this_dir_id, dir_list[1:])


def get_credentials():
    """
    Retrieves the credential from user's home directory. If credential
    does not exist, it opens a browser and authenticates

    Returns:
        An object of type oauth2client.client.Credentials
    """
    credential_path = path.join(get_gdrive_sync_home(), 'credential.json')
    store = file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets('client_secret.json', configs.get_config('DEFAULT', 'scopes'))
        flow.user_agent = configs.get_config('DEFAULT', 'application_name')
        credentials = tools.run_flow(flow, store, _Flags)
    return credentials


def get_service():
    """
    Returns:
        A googleapiclient.discovery.Resource object with methods for interacting with the service.
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    return discovery.build('drive', 'v3', http=http)


def get_inode_no(path_to_file):
    """
    Args:
        'A String' to the path of the file
    Retruns:
        A number. The inode number of the file
    """
    return os.stat(path_to_file).st_ino


def check_and_get_service(service=None):
    """
    If the input service is None, it creates a new one and returns.
    Else, returns the same object.
    Args:
        service: A googleapiclient.discovery.Resource object
    Return:
        service: A googleapiclient.discovery.Resource object
    """
    if not service:
        return get_service()
    return service


def delete_file_on_remote(remote_file_id, service=None):
    """
    Deletes the file/directory on google drive

    Args:
        remote_file_id: 'A String' id of the file/directory from google drive
        service: A googleapiclient.discovery.Resource object
    """
    check_and_get_service(service).files().delete(fileId=remote_file_id).execute()


def update_remote_file(remote_file_id, local_file_path, service=None):
    """
    Updates the content of the remote file with local file content
    Args:
        remote_file_id: 'A String' id of the file/directory from google drive
        local_file_path: 'A String' representation of the local file path
        service: A googleapiclient.discovery.Resource object
    """
    check_and_get_service(service).files().update(fileId=remote_file_id,
                                                  media_body=local_file_path,
                                                  media_mime_type=magic.from_file(local_file_path,
                                                                                  True)).execute()


def create_local_dir(dir_path):
    """
    Creates dir in the local filesystem
    :param dir_path:
    :return:
    """
    os.mkdir(dir_path, 0o755)


def delete_file_from_local(file_path):
    """
    Deletes a file or dir from local filesystem
    :param file_path: A string path to the file
    :return:
    """
    if os.path.isfile(file_path):
        os.remove(file_path)
    else:
        shutil.rmtree(file_path)