from unittest import TestCase
import os
from unittest.mock import Mock, patch, call
from unittest.case import skip
import time

from gdrive_sync.GdriveSync import GdriveSync
from gdrive_sync import utils, Db

logger = utils.create_logger(__name__)


class TestGdriveSync(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        self.gdriveSync = GdriveSync()

    def test_init(self):
        self.assertEqual({}, self.gdriveSync._local_dir_observer_dict)
        self.assertTrue(self.gdriveSync._db_handler)

    @skip("This needs to run manually")
    def test_process_dir_pairs_manual(self):
        self.gdriveSync._process_dir_pairs(utils.get_service(), {'/tmp/gdrive-sync/': '/test folder'})

    @patch('os.stat', autospec=True)
    @patch('gdrive_sync.utils.convert_rfc3339_time_to_epoch', autospec=True)
    @patch('gdrive_sync.utils.list_files_under_local_dir', autospec=True)
    @patch('gdrive_sync.utils.get_remote_files_from_dir', autospec=True)
    @patch('gdrive_sync.utils.get_remote_dir', autospec=True)
    def test_process_dir_pairs(self,
                               mock_get_remote_dir,
                               mock_get_remote_files_from_dir,
                               mock_list_files_under_local_dir,
                               mock_convert_rfc3339_time_to_epoch,
                               mock_os_stat):
        mocked_service = Mock()
        dir_pairs = {'/home/test1/child': '/test1/child'}
        mock_get_remote_dir.return_value = {'id': 'remote_dir_id', 'modifiedTime': 'test_modifiedTime'}
        mock_get_remote_files_from_dir.return_value = 'remote_files_under_dir'
        mock_list_files_under_local_dir.return_value = 'local_files_under_dir'
        self.gdriveSync._compare_and_sync_files = Mock()
        mock_convert_rfc3339_time_to_epoch.return_value = 101
        self.gdriveSync._db_handler = Mock(Db.DbHandler)
        mock_os_stat.return_value.st_mtime = 1001

        self.gdriveSync._process_dir_pairs(mocked_service, dir_pairs)

        mock_get_remote_dir.assert_called_once_with(mocked_service, 'root', ['test1', 'child'])
        mock_get_remote_files_from_dir.assert_called_once_with(mocked_service, 'remote_dir_id')
        mock_list_files_under_local_dir.assert_called_once_with('/home/test1/child')
        self.gdriveSync._compare_and_sync_files.assert_called_once_with(mocked_service,
                                                                        'remote_files_under_dir',
                                                                        'remote_dir_id',
                                                                        'local_files_under_dir',
                                                                        '/home/test1/child')
        mock_convert_rfc3339_time_to_epoch.assert_called_once_with('test_modifiedTime')
        self.gdriveSync._db_handler.insert_record.assert_called_once_with('/home/test1/child',
                                                                          'remote_dir_id',
                                                                          1001,
                                                                          101)

    @patch('gdrive_sync.utils.delete_file_on_remote', autospec=True)
    @patch('gdrive_sync.utils.create_local_dir', autospec=True)
    @patch('time.time', autospec=True)
    @patch('gdrive_sync.utils.copy_local_file_to_remote', autospec=True)
    @patch('gdrive_sync.utils.overwrite_remote_file_with_local', autospec=True)
    @patch('gdrive_sync.utils.copy_remote_file_to_local', autospec=True)
    @patch('gdrive_sync.utils.convert_rfc3339_time_to_epoch', autospec=True)
    def test_compare_and_sync_files(self,
                                    mock_convert_rfc3339_time_to_epoch,
                                    mock_copy_remote_file_to_local,
                                    mock_overwrite_remote_file_with_local,
                                    mock_copy_local_file_to_remote,
                                    mock_time,
                                    mock_create_local_dir,
                                    mock_delete_file_on_remote):
        mocked_service = Mock()

        # remote files mock
        remote_files = iter([{'id': '1', 'name': 'file1', 'modifiedTime': 'modifiedTime1', 'mimeType': 'file'},
                             {'id': '2', 'name': 'file2', 'modifiedTime': 'modifiedTime2', 'mimeType': 'file'},
                             {'id': '5', 'name': 'dir5', 'modifiedTime': 'modifiedTime5',
                              'mimeType': 'application/vnd.google-apps.folder',
                              'children': iter([{'id': '6', 'name': 'file6', 'modifiedTime': 'modifiedTime6',
                                                 'mimeType': 'file'}])},  # Dir
                             {'id': '3', 'name': 'file3', 'modifiedTime': 'modifiedTime3', 'mimeType': 'file'},
                             # remote file will be copied to local
                             {'id': '7', 'name': 'dir7', 'modifiedTime': 'modifiedTime7',
                              'mimeType': 'application/vnd.google-apps.folder',
                              'children': iter([{'id': '8', 'name': 'file8',
                                                 'modifiedTime': 'modifiedTime8', 'mimeType': 'file'}])},  # Dir

                             # Deleted from local
                             {'id': '9', 'name': 'dir9', 'modifiedTime': 'modifiedTime9',
                              'mimeType': 'application/vnd.google-apps.folder',
                              'children': iter([{'id': '10', 'name': 'file10',
                                                 'modifiedTime': 'modifiedTime10', 'mimeType': 'file'}])},
                             {'id': '11', 'name': 'file11', 'modifiedTime': 'modifiedTime11', 'mimeType': 'file'}
                             ])

        # local files mock
        local_file_mock_1 = Mock()
        local_file_mock_1.name = 'file1'
        local_file_mock_1.path = 'path1'
        local_file_mock_1.stat.return_value.st_mtime = 101.11
        local_file_mock_2 = Mock()
        local_file_mock_2.name = 'file2'
        local_file_mock_2.path = 'path2'
        local_file_mock_2.stat.return_value.st_mtime = 99
        local_file_mock_4 = Mock(name='file4', path='path4')
        local_file_mock_4.name = 'file4'
        local_file_mock_4.path = 'path4'
        local_file_mock_4.stat.return_value.st_mtime = 98
        local_dir_mock_5 = Mock(name='dir5', path='path4')
        local_dir_mock_5.name = 'dir5'
        local_dir_mock_5.path = 'path5'
        local_dir_mock_5.stat.return_value.st_mtime = 97
        local_file_mock_6 = Mock(name='file6', path='path6')
        local_file_mock_6.name = 'file4'
        local_file_mock_6.path = 'path4'
        local_file_mock_6.stat.return_value.st_mtime = 96
        local_files = [local_file_mock_1,  # local file will replace remote
                       local_file_mock_2,  # remote file will replace local
                       local_file_mock_4,  # local file will be copied to remote
                       {local_dir_mock_5: [local_file_mock_6]}  # local dir
                       ]
        # utils mocks
        mock_convert_rfc3339_time_to_epoch.return_value = 100
        mock_copy_local_file_to_remote.return_value = '4'

        # other mocks
        mock_time.return_value = 99999999.99
        self.gdriveSync._copy_local_to_remote = Mock()

        # db_handler mocks
        self.gdriveSync._db_handler = Mock(Db.DbHandler)
        self.gdriveSync._db_handler.get_local_modification_date.return_value = 80
        self.gdriveSync._db_handler.get_remote_modification_date.return_value = 80

        def get_local_file_path_effect(arg):
            if arg in ['9', '11']:
                return 'file_path'
            return None

        self.gdriveSync._db_handler.get_local_file_path.side_effect = get_local_file_path_effect

        # actual method call
        self.gdriveSync._compare_and_sync_files(mocked_service,
                                                remote_files,
                                                'remote_parent_dir_id1',
                                                local_files,
                                                'local_parent_dir1')

        # assertions
        mock_convert_rfc3339_time_to_epoch.assert_has_calls([call('modifiedTime1'),
                                                             call('modifiedTime2'),
                                                             call('modifiedTime6'),
                                                             call('modifiedTime3'),
                                                             call('modifiedTime7'),
                                                             call('modifiedTime8'), ])
        mock_overwrite_remote_file_with_local.assert_called_once_with(mocked_service,
                                                                      '1',
                                                                      'path1')
        mock_copy_remote_file_to_local.assert_has_calls([call(mocked_service,
                                                              'path2',
                                                              '2'),
                                                         call(mocked_service,
                                                              'local_parent_dir1/dir5/file6',
                                                              '6'),
                                                         call(mocked_service,
                                                              'local_parent_dir1/file3',
                                                              '3'),
                                                         call(mocked_service,
                                                              'local_parent_dir1/dir7/file8',
                                                              '8')])
        mock_create_local_dir.assert_called_once_with('local_parent_dir1/dir7')
        mock_delete_file_on_remote.assert_has_calls([call('9'), call('11')])

        self.gdriveSync._db_handler.insert_record.assert_has_calls([call('path1', '1', 101, 99999999),
                                                                    call('path2', '2', 99999999, 100),
                                                                    call('local_parent_dir1/dir5/file6', '6', 99999999,
                                                                         100),
                                                                    call('local_parent_dir1/file3', '3', 99999999, 100),
                                                                    call('local_parent_dir1/dir7', '7', 99999999, 100),
                                                                    call('local_parent_dir1/dir7/file8', '8', 99999999,
                                                                         100)])
        self.gdriveSync._db_handler.get_local_modification_date.assert_called_once_with('path1')
        self.gdriveSync._db_handler.get_remote_modification_date.assert_called_once_with('2')
        self.gdriveSync._db_handler.delete_record.assert_has_calls([call('local_parent_dir1/dir9'),
                                                                    call('local_parent_dir1/file11')])
        self.gdriveSync._copy_local_to_remote.assert_has_calls([call({'file4': local_file_mock_4},
                                                                     'remote_parent_dir_id1',
                                                                     mocked_service)])

    @patch('gdrive_sync.utils.delete_file_from_local', autospec=True)
    @patch('time.time', autospec=True)
    @patch('gdrive_sync.utils.copy_local_file_to_remote', autospec=True)
    @patch('gdrive_sync.utils.create_remote_dir', autospec=True)
    def test_copy_local_to_remote(self,
                                  mock_create_remote_dir,
                                  mock_copy_local_file_to_remote,
                                  mock_time,
                                  mock_delete_file_from_local):
        mocked_service = Mock()

        local_file_mock_1 = Mock()
        local_file_mock_1.name = 'file1'
        local_file_mock_1.path = 'path1'
        local_file_mock_1.stat.return_value.st_mtime = 98
        local_dir_mock_2 = Mock()
        local_dir_mock_2.name = 'dir2'
        local_dir_mock_2.path = 'path2'
        local_dir_mock_2.stat.return_value.st_mtime = 97
        local_file_mock_3 = Mock()
        local_file_mock_3.name = 'file3'
        local_file_mock_3.path = 'path3'
        local_file_mock_3.stat.return_value.st_mtime = 96
        local_file_mock_4 = Mock()
        local_file_mock_4.name = 'file4'
        local_file_mock_4.path = 'path4'
        local_dir_mock_5 = Mock()
        local_dir_mock_5.name = 'dir5'
        local_dir_mock_5.path = 'path5'
        local_file_mock_6 = Mock()
        local_file_mock_6.name = 'file6'
        local_file_mock_6.path = 'path6'
        local_files = {'dir2': {local_dir_mock_2: [local_file_mock_3]},
                       'file1': local_file_mock_1,
                       'dir5': {local_dir_mock_5: [local_file_mock_6]},
                       'file4': local_file_mock_4}

        mock_copy_local_file_to_remote.return_value = '1'
        mock_create_remote_dir.return_value = '2'
        mock_time.return_value = 99999999.99

        self.gdriveSync._db_handler = Mock(Db.DbHandler)

        def get_remote_file_id_side_effect(arg):
            if arg in ['path5', 'path4']:
                return 'valid id'
            else:
                return None

        self.gdriveSync._db_handler.get_remote_file_id.side_effect = get_remote_file_id_side_effect

        self.gdriveSync._copy_local_to_remote(local_files, 'remote_parent_dir_id', mocked_service)

        mock_create_remote_dir.assert_called_once_with('dir2', 'remote_parent_dir_id')
        mock_copy_local_file_to_remote.assert_has_calls([call('path3',
                                                              '2',
                                                              mocked_service),
                                                         call('path1',
                                                              'remote_parent_dir_id',
                                                              mocked_service)],
                                                        any_order=True)
        self.gdriveSync._db_handler.insert_record.assert_has_calls([call('path1', '1', 98, 99999999),
                                                                    call('path2', '2', 97, 99999999),
                                                                    call('path3', '1', 96, 99999999)],
                                                                   any_order=True)
        mock_delete_file_from_local.assert_has_calls([call('path5'),
                                                      call('path4')],
                                                     any_order=True)
        self.gdriveSync._db_handler.delete_record.assert_has_calls([call('path5'),
                                                                    call('path4')],
                                                                   any_order=True)

    @patch('gdrive_sync.utils.get_service', autospec=True)
    def test_sync_onetime(self, mocked_get_service):
        mocked_get_service.return_value = 'service'
        self.gdriveSync._process_dir_pairs = Mock()

        self.gdriveSync.sync_onetime('synced_dirs_dict')

        mocked_get_service.assert_called_once_with()
        self.gdriveSync._process_dir_pairs.assert_called_once_with('service', 'synced_dirs_dict')

    @patch('watchdog.observers.Observer', autospec=True)
    @patch('gdrive_sync.LocalFSEventHandler.LocalFSEventHandler', autospec=True)
    def test_watch_local_dir(self, mock_LocalFSEventHandler, mock_observer):
        mock_LocalFSEventHandler.return_value = 'event_hanlder'

        self.assertEqual(mock_observer.return_value,
                         self.gdriveSync._watch_local_dir('dir_to_watch'))

        mock_LocalFSEventHandler.assert_called_once_with(self.gdriveSync._db_handler)
        mock_observer.assert_called_once_with()
        mock_observer.return_value.schedule('event_handler',
                                            'dir_to_watch',
                                            recursive=True)

        mock_observer.return_value.start.assert_called_once_with()

    @skip("This needs to run manually")
    def test_watch_local_dir_manual(self):
        logger.info('Starting _process_dir_pairs')
        self.gdriveSync._process_dir_pairs(utils.get_service(), {'/tmp/gdrive-sync': '/test folder'})
        logger.info('Starting _watch_local_dir')
        self.gdriveSync._watch_local_dir('/tmp/gdrive-sync/')
        try:
            logger.info('Sleeping')
            time.sleep(600)
        except KeyboardInterrupt:
            logger.info('Interrupted')
        logger.info('Stopping sync')
        self.gdriveSync.stop_sync()
