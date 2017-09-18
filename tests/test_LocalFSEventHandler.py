import unittest
import os
from unittest.mock import Mock, patch

os.chdir('../gdrive_sync')
from gdrive_sync.LocalFSEventHandler import LocalFSEventHandler 

class TestLocalFSEventHandler(unittest.TestCase):
    
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.mock_db_handler = Mock()
        self.localFSEventHandler = LocalFSEventHandler(self.mock_db_handler)
    
    def test_init(self):
        self.assertEqual(self.mock_db_handler,
                         self.localFSEventHandler._db_handler)
    
    @patch('os.path.dirname', autospec=True)
    @patch('gdrive_sync.utils.copy_local_file_to_remote', autospec=True)
    def test_on_created(self, 
                        mock_copy_local_file_to_remote,
                        mock_path_dirname):
        mock_event = Mock()
        mock_event.src_path = 'path_to_file'
        mock_event.is_directory = False
        self.mock_db_handler.get_remote_file_id.return_value = 'remote_file_id'
        mock_path_dirname.return_value = 'path_to_parent_dir'
        
        self.localFSEventHandler.on_created(mock_event)
        
        mock_path_dirname.assert_called_once_with('path_to_file')
        self.mock_db_handler.get_remote_file_id.assert_called_once_with('path_to_parent_dir')
        mock_copy_local_file_to_remote.assert_called_once_with('path_to_file', 'remote_file_id')
    
    @patch('gdrive_sync.utils.update_remote_file', autospec=True)
    def test_on_modified(self, 
                         mock_update_remote_file):
        mock_event = Mock()
        mock_event.src_path = 'path_to_file'
        mock_event.is_directory = False
        self.mock_db_handler.get_remote_file_id.return_value = 'remote_file_id'
        
        self.localFSEventHandler.on_modified(mock_event)
        
        self.mock_db_handler.get_remote_file_id.assert_called_once_with('path_to_file')
        mock_update_remote_file.assert_called_once_with('remote_file_id', 
                                                        'path_to_file')
    
    @patch('gdrive_sync.utils.delete_file_on_remote', autospec=True)
    def test_on_deleted(self, mock_delete_file_on_remote):
        mock_event = Mock()
        mock_event.src_path = 'path_to_file'
        self.mock_db_handler.get_remote_file_id.return_value = 'remote_file_id'
        
        self.localFSEventHandler.on_deleted(mock_event)
        
        self.mock_db_handler.get_remote_file_id.assert_called_once_with('path_to_file')
        mock_delete_file_on_remote.assert_called_once_with('remote_file_id')