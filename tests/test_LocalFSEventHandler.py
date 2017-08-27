import unittest
import os
from unittest.mock import Mock, patch

os.chdir('../gdrive_sync')
from gdrive_sync.LocalFSEventHandler import LocalFSEventHandler 

class TestLocalFSEventHandler(unittest.TestCase):
    
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.mock_remote_file_id_dict = Mock()
        self.localFSEventHandler = LocalFSEventHandler(self.mock_remote_file_id_dict)
    
    def test_init(self):
        self.assertEqual(self.mock_remote_file_id_dict,
                         self.localFSEventHandler._remote_file_id_dict)
    
    @patch('os.path.dirname', autospec=True)
    @patch('gdrive_sync.utils.get_inode_no', autospec=True)
    @patch('gdrive_sync.utils.copy_local_file_to_remote', autospec=True)
    def test_on_created(self, mock_copy_local_file_to_remote, mock_get_inode_no, mock_path_dirname):
        mock_event = Mock()
        mock_event.src_path = 'path_to_file'
        mock_event.is_directory = False
        self.mock_remote_file_id_dict.__getitem__ = Mock(return_value = 'remote_file_id')
        mock_path_dirname.return_value = 'path_to_parent_dir'
        mock_get_inode_no.return_value = 101
        
        self.localFSEventHandler.on_created(mock_event)
        
        mock_path_dirname.assert_called_once_with('path_to_file')
        mock_get_inode_no.assert_called_once_with('path_to_parent_dir')
        self.mock_remote_file_id_dict.__getitem__.assert_called_once_with(101)
        mock_copy_local_file_to_remote.assert_called_once_with('path_to_file', 'remote_file_id')
    
    @patch('os.path.dirname', autospec=True)
    @patch('gdrive_sync.utils.get_inode_no', autospec=True)
    @patch('gdrive_sync.utils.copy_local_file_to_remote', autospec=True)
    def test_on_modified(self, mock_copy_local_file_to_remote, mock_get_inode_no, mock_path_dirname):
        mock_event = Mock()
        mock_event.src_path = 'path_to_file'
        mock_event.is_directory = False
        self.mock_remote_file_id_dict.__getitem__ = Mock(return_value = 'remote_file_id')
        mock_path_dirname.return_value = 'path_to_parent_dir'
        mock_get_inode_no.return_value = 101
        
        self.localFSEventHandler.on_modified(mock_event)
        
        mock_path_dirname.assert_called_once_with('path_to_file')
        mock_get_inode_no.assert_called_once_with('path_to_parent_dir')
        self.mock_remote_file_id_dict.__getitem__.assert_called_once_with(101)
        mock_copy_local_file_to_remote.assert_called_once_with('path_to_file', 'remote_file_id')
    
    @patch('gdrive_sync.utils.get_inode_no', autospec=True)
    @patch('gdrive_sync.utils.delete_file_on_remote', autospec=True)
    def test_on_deleted(self, mock_delete_file_on_remote, mock_get_inode_no):
        mock_event = Mock()
        mock_event.src_path = 'path_to_file'
        mock_get_inode_no.return_value = 101
        self.mock_remote_file_id_dict.__getitem__ = Mock(return_value = 'remote_file_id')
        
        self.localFSEventHandler.on_deleted(mock_event)
        
        mock_get_inode_no.assert_called_once_with('path_to_file')
        self.mock_remote_file_id_dict.__getitem__.assert_called_once_with(101)
        mock_delete_file_on_remote.assert_called_once_with('remote_file_id')