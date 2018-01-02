import unittest
import os
from unittest.mock import Mock, patch, call

from gdrive_sync.LocalFSEventHandler import LocalFSEventHandler 

class TestLocalFSEventHandler(unittest.TestCase):
    
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.mock_db_handler = Mock()
        self.localFSEventHandler = LocalFSEventHandler(self.mock_db_handler)
    
    def test_init(self):
        self.assertEqual(self.mock_db_handler,
                         self.localFSEventHandler._db_handler)
    
    @patch('time.time', autospec=True)
    @patch('os.path.dirname', autospec=True)
    @patch('gdrive_sync.utils.copy_local_file_to_remote', autospec=True)
    def test_on_created(self, 
                        mock_copy_local_file_to_remote,
                        mock_path_dirname,
                        mock_time):
        mock_event = Mock()
        mock_event.src_path = 'path_to_file'
        mock_event.is_directory = False
        self.mock_db_handler.get_remote_file_id.return_value = 'remote_parent_dir_id'
        mock_path_dirname.return_value = 'path_to_parent_dir'
        mock_time.return_value = 1001
        mock_copy_local_file_to_remote.return_value = 'remote_file_id'
        
        self.localFSEventHandler.on_created(mock_event)
        
        mock_path_dirname.assert_called_once_with('path_to_file')
        self.mock_db_handler.get_remote_file_id.assert_called_once_with('path_to_parent_dir')
        mock_copy_local_file_to_remote.assert_called_once_with('path_to_file', 'remote_parent_dir_id')
        self.mock_db_handler.insert_record.assert_called_once_with('path_to_file', 
                                                                   'remote_file_id',
                                                                   1001,
                                                                   1001)
    
    @patch('time.time', autospec=True)
    @patch('gdrive_sync.utils.update_remote_file', autospec=True)
    def test_on_modified(self, 
                         mock_update_remote_file,
                         mock_time):
        mock_event = Mock()
        mock_event.src_path = 'path_to_file'
        mock_event.is_directory = False
        self.mock_db_handler.get_remote_file_id.return_value = 'remote_file_id'
        mock_time.return_value = 1001
        
        self.localFSEventHandler.on_modified(mock_event)
        
        self.mock_db_handler.get_remote_file_id.assert_called_once_with('path_to_file')
        mock_update_remote_file.assert_called_once_with('remote_file_id', 
                                                        'path_to_file')
        self.mock_db_handler.update_record.assert_called_once_with('path_to_file', 
                                                                   'remote_file_id',
                                                                   1001,
                                                                   1001)
    
    @patch('gdrive_sync.utils.delete_file_on_remote', autospec=True)
    def test_on_deleted(self, mock_delete_file_on_remote):
        mock_event = Mock()
        mock_event.src_path = 'path_to_file'
        self.mock_db_handler.get_remote_file_id.return_value = 'remote_file_id'
        
        self.localFSEventHandler.on_deleted(mock_event)
        
        self.mock_db_handler.get_remote_file_id.assert_called_once_with('path_to_file')
        mock_delete_file_on_remote.assert_called_once_with('remote_file_id')
        self.mock_db_handler.delete_record.assert_called_once_with('path_to_file')
    
    @patch('time.time', autospec=True)
    @patch('os.path.dirname', autospec=True)
    @patch('gdrive_sync.utils.copy_local_file_to_remote', autospec=True)
    @patch('gdrive_sync.utils.delete_file_on_remote', autospec=True)
    def test_on_moved(self, 
                      mock_delete_file_on_remote, 
                      mock_copy_local_file_to_remote,
                      mock_path_dirname,
                      mock_time):
        
        mock_event = Mock()
        mock_event.src_path = 'path_to_file'
        mock_event.dest_path = 'new_path_to_file'
        mock_event.is_directory = False
        self.mock_db_handler.get_remote_file_id.side_effect = ['remote_file_id_old', 'remote_parent_dir_id']
        mock_path_dirname.return_value = 'path_to_parent_dir'
        mock_time.return_value = 1001
        mock_copy_local_file_to_remote.return_value = 'remote_file_id_new'
        
        self.localFSEventHandler.on_moved(mock_event)
        
        mock_delete_file_on_remote.assert_called_once_with('remote_file_id_old')
        self.mock_db_handler.get_remote_file_id.assert_has_calls([call('path_to_file'),
                                                                  call('path_to_parent_dir')])
        mock_copy_local_file_to_remote.assert_called_once_with('new_path_to_file', 'remote_parent_dir_id')
        self.mock_db_handler.insert_record.assert_called_once_with('new_path_to_file', 'remote_file_id_new', 1001, 1001)