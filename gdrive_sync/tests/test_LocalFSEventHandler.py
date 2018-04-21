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
    @patch('os.path.basename', autospec=True)
    @patch('gdrive_sync.utils.create_remote_dir', autospec=True)
    @patch('gdrive_sync.utils.copy_local_file_to_remote', autospec=True)
    def test_on_created(self,
                        mock_copy_local_file_to_remote,
                        mock_create_remote_dir,
                        mock_path_basename,
                        mock_path_dirname,
                        mock_time):
        mock_event_file = Mock()
        mock_event_file.src_path = 'path_to_file'
        mock_event_file.is_directory = False
        self.mock_db_handler.get_remote_file_id.return_value = 'remote_parent_dir_id'
        mock_path_basename.return_value = 'dir_name'
        mock_path_dirname.return_value = 'path_to_parent_dir'
        mock_time.side_effect = [1001, 1001, 1002, 1002]
        mock_copy_local_file_to_remote.return_value = 'remote_file_id'

        self.localFSEventHandler.on_created(mock_event_file)

        mock_event_dir = Mock()
        mock_event_dir.src_path = 'path_to_dir'
        mock_event_dir.is_directory = True
        mock_create_remote_dir.return_value = 'remote_dir_id'

        self.localFSEventHandler.on_created(mock_event_dir)

        mock_path_dirname.assert_has_calls([call('path_to_file'),
                                            call('path_to_dir')])
        self.mock_db_handler.get_remote_file_id.assert_has_calls([call('path_to_parent_dir'),
                                                                  call('path_to_parent_dir')])
        mock_copy_local_file_to_remote.assert_called_once_with('path_to_file', 'remote_parent_dir_id')
        mock_create_remote_dir.assert_called_once_with('dir_name', 'remote_parent_dir_id')
        self.mock_db_handler.insert_record.assert_has_calls([call('path_to_file',
                                                                  'remote_file_id',
                                                                  1001,
                                                                  1001),
                                                             call('path_to_dir',
                                                                  'remote_dir_id',
                                                                  1002,
                                                                  1002)
                                                             ])

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

    @patch('gdrive_sync.utils.create_remote_dir', autospec=True)
    @patch('os.path.basename', autospec=True)
    @patch('time.time', autospec=True)
    @patch('os.path.dirname', autospec=True)
    @patch('gdrive_sync.utils.copy_local_file_to_remote', autospec=True)
    @patch('gdrive_sync.utils.delete_file_on_remote', autospec=True)
    def test_on_moved(self,
                      mock_delete_file_on_remote,
                      mock_copy_local_file_to_remote,
                      mock_path_dirname,
                      mock_time,
                      mock_path_basename,
                      mock_create_remote_dir):

        mock_event = Mock()
        mock_event.src_path = 'path_to_file'
        mock_event.dest_path = 'new_path_to_file'
        mock_event.is_directory = False
        self.mock_db_handler.get_remote_file_id.side_effect = ['remote_file_id_old', 
                                                               'remote_parent_dir_id',
                                                               'remote_file_id_old', 
                                                               'remote_parent_dir_id']
        mock_path_dirname.return_value = 'path_to_parent_dir'
        mock_time.return_value = 1001
        mock_copy_local_file_to_remote.return_value = 'remote_file_id_new'

        self.localFSEventHandler.on_moved(mock_event)
        
        mock_event.is_directory = True
        mock_event.src_path = 'path_to_dir'
        mock_event.dest_path = 'new_path_to_dir'
        mock_path_basename.return_value = 'new_dir_name'
        mock_create_remote_dir.return_value = 'remote_dir_id_new'
        
        self.localFSEventHandler.on_moved(mock_event)

        mock_delete_file_on_remote.assert_has_calls([call('remote_file_id_old'), 
                                                     call('remote_file_id_old')])
        self.mock_db_handler.get_remote_file_id.assert_has_calls([call('path_to_file'),
                                                                  call('path_to_parent_dir'),
                                                                  call('path_to_dir'),
                                                                  call('path_to_parent_dir')])
        mock_copy_local_file_to_remote.assert_called_once_with('new_path_to_file', 'remote_parent_dir_id')
        self.mock_db_handler.insert_record.assert_has_calls([call('new_path_to_file', 
                                                                  'remote_file_id_new', 
                                                                  1001, 
                                                                  1001),
                                                             call('new_path_to_dir', 
                                                                  'remote_dir_id_new', 
                                                                  1001, 
                                                                  1001)])
