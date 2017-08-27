from watchdog.events import FileSystemEventHandler
from gdrive_sync import utils
import os

logger = utils.create_logger(__name__)

class LocalFSEventHandler(FileSystemEventHandler):
    
    def __init__(self, remote_file_id_dict, *args, **kwargs):
        '''
        Args:
            remote_file_id_dict: A dict comprised of local file inode numbers
                and remote file id 
        '''
        FileSystemEventHandler.__init__(self, *args, **kwargs)
        self._remote_file_id_dict = remote_file_id_dict
    
    def on_any_event(self, event):
        pass
    
    def on_created(self, event):
        logger.debug('Created {}'.format(event.src_path))
        if event.is_directory:
            pass #utils.create_remote_dir
        else:
            utils.copy_local_file_to_remote(event.src_path, 
                                            self._remote_file_id_dict[
                                                utils.get_inode_no(
                                                    os.path.dirname(
                                                        event.src_path))])
        
    def on_deleted(self, event):
        logger.debug('Deleted {}'.format(event.src_path))
        utils.delete_file_on_remote(
            self._remote_file_id_dict[
                utils.get_inode_no(
                    event.src_path)])
    
    def on_modified(self, event):
        logger.debug('Modified {}'.format(event.src_path))
        if event.is_directory:
            pass #utils.copy_dir_to_remote
        else:
            utils.copy_local_file_to_remote(event.src_path, 
                                            self._remote_file_id_dict[
                                                utils.get_inode_no(
                                                    os.path.dirname(
                                                        event.src_path))])
    
    def on_moved(self, event):
        logger.debug('Moved from {} to {}'.format(event.src_path, event.dest_path))
        pass