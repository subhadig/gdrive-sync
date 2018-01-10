import os
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock, call, create_autospec

from gdrive_sync import utils


class TestUtils(TestCase):

    def test_get_gdrive_sync_home(self):
        self.assertTrue(os.path.exists(utils.get_gdrive_sync_home()))
        self.assertEqual(os.path.expanduser('~') + '/.gdrive-sync', utils.get_gdrive_sync_home())

    def test_create_logger(self):
        logger = utils.create_logger(__name__)
        self.assertTrue(logger, 'A logger should be returned.')
        logger.info('Test logging')

    def test_get_user_settings(self):
        settings = utils.get_user_settings()
        self.assertTrue(settings)
        self.assertIsNotNone(settings['synced_dirs'])

    def test_store_user_settings(self):
        utils.store_user_settings(utils._user_settings_template)

    def test_list_drive_files(self):
        mocked_service = Mock()

        utils.list_drive_files(mocked_service, "fields", query="query")

        mocked_service.files.assert_called_once_with()
        mocked_service.files.return_value.list.assert_called_once_with(
            q="query", corpora="user", fields="fields", pageToken=None)
        mocked_service.files.return_value.list.return_value.execute.assert_called_once_with()

    @patch('os.scandir', autospec=True)
    def test_list_files_under_local_dir(self, mock_scandir):
        mock_direntry_1 = Mock()
        mock_direntry_1.is_dir.return_value = False
        mock_direntry_2 = Mock()
        mock_direntry_2.is_dir.return_value = True
        mock_direntry_2.path = '/path/to/some/dir'
        mock_direntry_3 = Mock()
        mock_direntry_3.is_dir.return_value = False
        mock_scandir.side_effect = [[mock_direntry_1, mock_direntry_2], [mock_direntry_3]]

        # self.assertEqual([mock_direntry_1, {mock_direntry_2: [mock_direntry_3]}],
        #                  utils.list_files_under_local_dir('dir_path'))
        result_iter = utils.list_files_under_local_dir('dir_path')

        self.assertEqual(mock_direntry_1, next(result_iter))
        tmp_next = next(result_iter)
        key = next(iter(tmp_next))
        self.assertEqual(mock_direntry_2, key)
        self.assertEqual(mock_direntry_3, next(tmp_next[key]))

        mock_scandir.assert_has_calls([call(path='dir_path'), call(path='/path/to/some/dir')])

    def test_convert_rfc3339_time_to_epoch(self):
        self.assertEqual(1498620320, utils.convert_rfc3339_time_to_epoch('2017-06-28T03:25:20.954Z'))

    def test_convert_epoch_time_to_rfc3339(self):
        self.assertEqual('2017-06-28T03:25:20Z', utils.convert_epoch_time_to_rfc3339(1498620320))

    @patch('magic.from_file', autospec=True)
    def test_overwrite_remote_file_with_local(self, mocked_magic):
        mocked_service = Mock()
        mocked_service.files.return_value.update.return_value.execute.return_value = 'final return'
        mocked_magic.return_value = 'test_mime_type'

        self.assertEqual('final return', utils.overwrite_remote_file_with_local(
            mocked_service, 'test id', 'test path'))

        mocked_service.files.assert_called_once_with()
        mocked_service.files.return_value.update.assert_called_once_with(fileId='test id',
                                                                         media_body='test path',
                                                                         media_mime_type='test_mime_type')
        mocked_service.files.return_value.update.return_value.execute.assert_called_once_with()
        mocked_magic.assert_called_once_with('test path', True)

    def test_copy_remote_file_to_local(self):
        mocked_service = Mock()
        mocked_service.files.return_value.get_media.return_value.execute.return_value = b'test content'

        utils.copy_remote_file_to_local(mocked_service,
                                        '/tmp/gdrive_test.txt',
                                        'Test id')

        mocked_service.files.assert_called_once_with()
        mocked_service.files.return_value.get_media.assert_called_once_with(fileId='Test id')
        mocked_service.files.return_value.get_media.return_value.execute.assert_called_once_with()
        with open('/tmp/gdrive_test.txt', 'r') as file:
            self.assertEqual('test content', file.read())
        os.remove('/tmp/gdrive_test.txt')

    @patch('magic.from_file', autospec=True)
    @patch('os.path.basename', autospec=True)
    @patch('gdrive_sync.utils.check_and_get_service', autospec=True)
    def test_copy_local_file_to_remote(self,
                                       check_and_get_service_mock,
                                       path_basename_mock,
                                       mocked_magic):
        mocked_service = Mock()
        mocked_service.files.return_value.create.return_value.execute.return_value = {'id': 'id1'}
        check_and_get_service_mock.return_value = mocked_service
        path_basename_mock.return_value = 'file'
        mocked_magic.return_value = 'test_mime_type'

        self.assertEqual('id1',
                         utils.copy_local_file_to_remote('/path/to/local/file',
                                                         'test_remote_parent_dir_id',
                                                         'service'))

        mocked_service.files.assert_called_once_with()
        mocked_service.files.return_value.create.assert_called_once_with(
            body={'parents': ['test_remote_parent_dir_id'], 'name': 'file'},
            media_body='/path/to/local/file',
            media_mime_type='test_mime_type')
        mocked_service.files.return_value.create.return_value.execute.assert_called_once_with()
        check_and_get_service_mock.assert_called_once_with('service')
        mocked_magic.assert_called_once_with('/path/to/local/file', True)

        self.assertEqual('id1',
                         utils.copy_local_file_to_remote('/path/to/local/file',
                                                         'test_remote_parent_dir_id'))

    def test_get_remote_files_from_dir(self):
        mocked_service = Mock()
        mocked_result_1 = {'files': ['file1', 'file2'], 'nextPageToken': 'nextPageToken'}
        mocked_result_2 = {'files': ['file3', 'file4']}
        mocked_list_drive_files = Mock(side_effect=[mocked_result_1, mocked_result_2])

        with patch('gdrive_sync.utils.list_drive_files', mocked_list_drive_files):
            self.assertEqual(['file3', 'file4', 'file1', 'file2'],
                             [x for x in utils.get_remote_files_from_dir(mocked_service, 'test_parent_dir_id')])

        calls = [call(mocked_service,
                      'nextPageToken, files(id, name, modifiedTime, mimeType)',
                      query="'test_parent_dir_id' in parents and trashed = false",
                      next_page_token=None),
                 call(mocked_service,
                      'nextPageToken, files(id, name, modifiedTime, mimeType)',
                      query="'test_parent_dir_id' in parents and trashed = false",
                      next_page_token='nextPageToken')]
        mocked_list_drive_files.assert_has_calls(calls)

    @patch('gdrive_sync.utils.get_remote_files_from_dir', autospec=True)
    def test_list_remote_files_from_dir_new(self,
                                            mock_get_remote_files_from_dir):
        mock_file = {'mimeType': 'not_dir', 'id': 1}
        mock_dir = {'mimeType': 'application/vnd.google-apps.folder', 'id': 1}
        mock_get_remote_files_from_dir.side_effect = [[mock_file, mock_dir], [mock_file]].__iter__()

        result_iter = utils.list_remote_files_from_dir(Mock(name='service'), 'parent_dir_id')

        self.assertEqual(mock_file, next(result_iter))
        self.assertEqual(mock_dir, next(result_iter))
        self.assertEqual(mock_file, next(mock_dir['children']))

    def test_get_remote_dir(self):
        mocked_service = Mock()
        mocked_result_1 = {'files': [{'id': 'id_1', 'modifiedTime': ', modifiedTime_1'}]}
        mocked_result_2 = {'files': [{'id': 'id_2', 'modifiedTime': ', modifiedTime_1'}]}
        mocked_list_drive_files = Mock(side_effect=[mocked_result_1, mocked_result_2])

        with patch('gdrive_sync.utils.list_drive_files', mocked_list_drive_files):
            self.assertEqual({'id': 'id_2', 'modifiedTime': ', modifiedTime_1'},
                             utils.get_remote_dir(mocked_service, 'root', ['dir1', 'dir2']))

        calls = [call(mocked_service,
                      "nextPageToken, files(id, modifiedTime)",
                      query="'root' in parents and name = 'dir1'"),
                 call(mocked_service,
                      "nextPageToken, files(id, modifiedTime)",
                      query="'id_1' in parents and name = 'dir2'")]
        mocked_list_drive_files.assert_has_calls(calls)

    @patch('oauth2client.tools.run_flow', autospec=True)
    @patch('oauth2client.client.flow_from_clientsecrets', autospec=True)
    @patch('oauth2client.file.Storage', autospec=True)
    @patch('gdrive_sync.utils.get_gdrive_sync_home', autospec=True)
    @patch('os.path.join', autospec=True)
    def test_get_credentials(self, mock_path_join, mock_get_gdrive_sync_home, mocked_storage,
                             mocked_flow_from_clientsecrets, mocked_run_flow):
        mock_path_join.return_value = 'credential_path'
        mock_get_gdrive_sync_home.return_value = 'gdrive_sync_home'
        mocked_store = Mock()
        mocked_storage.return_value = mocked_store
        mocked_credential = Mock()
        mocked_store.get.return_value = mocked_credential
        mocked_credential.invalid = True
        mocked_flow = Mock()
        mocked_flow_from_clientsecrets.return_value = mocked_flow
        mocked_run_flow.return_value = 'credentials'

        self.assertEqual('credentials', utils.get_credentials())

        mock_path_join.assert_called_once_with('gdrive_sync_home',
                                               'credential.json')
        mock_get_gdrive_sync_home.assert_called_once_with()
        mocked_storage.assert_called_once_with('credential_path')
        mocked_store.get.assert_called_once_with()
        mocked_flow_from_clientsecrets.assert_called_once_with('client_secret.json',
                                                               'https://www.googleapis.com/auth/drive')
        self.assertEqual('Gdrive Sync', mocked_flow.user_agent)
        mocked_run_flow.assert_called_once_with(mocked_flow, mocked_store, utils._Flags)

        mocked_credential.invalid = False
        mock_get_gdrive_sync_home.reset_mock()
        mocked_storage.reset_mock()
        mocked_store.reset_mock()

        self.assertEqual(mocked_credential, utils.get_credentials())

        mock_get_gdrive_sync_home.assert_called_once_with()
        mocked_storage.assert_called_once_with('credential_path')
        mocked_store.get.assert_called_once_with()

    @patch('httplib2.Http', autospec=True)
    @patch('googleapiclient.discovery.build', autospec=True)
    @patch('gdrive_sync.utils.get_credentials', autospec=True)
    def test_get_service(self, mocked_get_credentials, mocked_build, http_mock):
        mocked_credentials = Mock()
        mocked_get_credentials.return_value = mocked_credentials
        mocked_build.return_value = 'service'
        mocked_credentials.authorize.return_value = 'authorized'
        http_mock.return_value = 'http11'

        self.assertEqual('service', utils.get_service())

        mocked_get_credentials.assert_called_once_with()
        http_mock.assert_called_once_with()
        mocked_credentials.authorize.assert_called_once_with('http11')
        mocked_build.assert_called_once_with('drive', 'v3', http='authorized')

    @patch('os.stat', autospec=True)
    def test_get_inode_no(self, os_stat_mock):
        os_stat_mock.return_value = Mock()
        os_stat_mock.return_value.st_ino = 101

        self.assertEqual(101, utils.get_inode_no('path'))

        os_stat_mock.assert_called_once_with('path')

    @patch('gdrive_sync.utils.get_service', autospec=True)
    def test_check_and_get_service(self, mock_get_service):
        mock_get_service.return_value = 'service'

        self.assertEqual('service_1', utils.check_and_get_service('service_1'))
        self.assertEqual('service', utils.check_and_get_service())

        mock_get_service.assert_called_once_with()

    @patch('gdrive_sync.utils.check_and_get_service', autospec=True)
    def test_delete_file_on_remote(self, mock_check_and_get_service):
        mocked_service = Mock()
        mock_check_and_get_service.return_value = mocked_service

        utils.delete_file_on_remote('remote_file_id')

        mock_check_and_get_service.assert_called_once_with(None)
        mocked_service.files.assert_called_once_with()
        mocked_service.files.return_value.delete.assert_called_once_with(fileId='remote_file_id')
        mocked_service.files.return_value.delete.return_value.execute.assert_called_once_with()

    @patch('magic.from_file', autospec=True)
    @patch('gdrive_sync.utils.check_and_get_service', autospec=True)
    def test_update_remote_file(self, mock_check_and_get_service, mocked_magic):
        mocked_service = Mock()
        mock_check_and_get_service.return_value = mocked_service
        mocked_magic.return_value = 'test_mime_type'

        utils.update_remote_file('remote_file_id', 'local_file_path')

        mock_check_and_get_service.assert_called_once_with(None)
        mocked_service.files.assert_called_once_with()
        mocked_service.files.return_value.update.assert_called_once_with(fileId='remote_file_id',
                                                                         media_body='local_file_path',
                                                                         media_mime_type='test_mime_type')
        mocked_service.files.return_value.update.return_value.execute.assert_called_once_with()
        mocked_magic.assert_called_once_with('local_file_path', True)

    @patch('os.mkdir', autospec=True)
    def test_create_local_dir(self, mock_mkdir):
        utils.create_local_dir('dir_path')

        mock_mkdir.assert_called_once_with('dir_path', 0o755)

    @patch('shutil.rmtree', autospec=True)
    @patch('os.remove', autospec=True)
    @patch('os.path.isfile', autospec=True)
    def test_delete_file_from_local(self,
                                    isfile_mock,
                                    remove_mock,
                                    rmtree_mock):
        isfile_mock.side_effect = [True, False]

        utils.delete_file_from_local('file')
        utils.delete_file_from_local('dir')

        remove_mock.assert_called_once_with('file')
        rmtree_mock.assert_called_once_with('dir')