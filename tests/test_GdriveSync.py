from unittest import TestCase
import os
from unittest.mock import Mock, patch, call
from unittest.case import skip
import time

os.chdir('../gdrive_sync')
from gdrive_sync.GdriveSync import GdriveSync
from gdrive_sync import utils

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
    
    @patch('gdrive_sync.utils.convert_rfc3339_time_to_epoch', autospec=True)
    @patch('gdrive_sync.utils.list_files_under_local_dir', autospec=True)
    @patch('gdrive_sync.utils.get_remote_files_from_dir', autospec=True)
    @patch('gdrive_sync.utils.get_remote_dir', autospec=True)
    def test_process_dir_pairs(self, 
                               mock_get_remote_dir, 
                               mock_get_remote_files_from_dir, 
                               mock_list_files_under_local_dir,
                               mock_convert_rfc3339_time_to_epoch):
        mocked_service = Mock()
        dir_pairs = {'/home/test1/child': '/test1/child'}
        mock_get_remote_dir.return_value = {'id': 'remote_dir_id', 'modifiedTime': 'test_modifiedTime'} 
        mock_get_remote_files_from_dir.return_value = 'remote_files_under_dir'
        mock_list_files_under_local_dir.return_value = 'local_files_under_dir'
        self.gdriveSync._compare_and_sync_files = Mock()
        mock_convert_rfc3339_time_to_epoch.return_value = 101
        self.gdriveSync._db_handler = Mock()
        
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
                                                                          101)
    
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
                                    mock_time):
        mocked_service = Mock()
        remote_files = [{'id': '1', 'name': 'file1', 'modifiedTime': 'modifiedTime1'},
                        {'id': '2', 'name': 'file2', 'modifiedTime': 'modifiedTime2'},
                        {'id': '3', 'name': 'file3', 'modifiedTime': 'modifiedTime3'}] #remote file will be copied to local
        local_file_mock_1 = Mock()
        local_file_mock_1.name = 'file1'
        local_file_mock_1.path = 'path1'
        local_file_mock_1.stat.return_value.st_mtime = 101
        local_file_mock_1.inode.return_value = 1001
        local_file_mock_2 = Mock()
        local_file_mock_2.name = 'file2'
        local_file_mock_2.path = 'path2'
        local_file_mock_2.stat.return_value.st_mtime = 99
        local_file_mock_2.inode.return_value = 1002
        local_file_mock_4 = Mock(name='file4', path='path4')
        local_file_mock_4.name = 'file4'
        local_file_mock_4.path = 'path4'
        local_file_mock_4.inode.return_value = 1004
        local_files = [local_file_mock_1, #local file will replace remote 
                       local_file_mock_2, #remote file will replace local
                       local_file_mock_4] #local file will be copied to remote
        mock_convert_rfc3339_time_to_epoch.return_value = 100
        mock_copy_local_file_to_remote.return_value = '4'
        mock_time.return_value = 101
        self.gdriveSync._db_handler = Mock()
        
        self.gdriveSync._compare_and_sync_files(mocked_service, 
                                                remote_files, 
                                                'remote_parent_dir_id1', 
                                                local_files, 
                                                'local_parent_dir1')
        
        mock_convert_rfc3339_time_to_epoch.assert_has_calls([call('modifiedTime1'),
                                                               call('modifiedTime2')])
        mock_overwrite_remote_file_with_local.assert_called_once_with(mocked_service,
                                                                      '1',
                                                                      'path1')
        mock_copy_remote_file_to_local.assert_has_calls([call(mocked_service,
                                                                'path2',
                                                                '2'),
                                                           call(mocked_service,
                                                                'local_parent_dir1/file3',
                                                                '3')])
        mock_copy_local_file_to_remote.assert_called_once_with('path4',
                                                               'remote_parent_dir_id1',
                                                               mocked_service)
        self.gdriveSync._db_handler.insert_record.assert_has_calls([call('path1', '1', 100),
                                                      call('path2', '2', 101),
                                                      call('path4', '4', 101),
                                                      call('local_parent_dir1/file3', '3', 101)])
    
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