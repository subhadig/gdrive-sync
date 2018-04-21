from watchdog.events import FileSystemEventHandler
from gdrive_sync import utils
import os
import time

logger = utils.create_logger(__name__)


class LocalFSEventHandler(FileSystemEventHandler):

    def __init__(self, db_handler):
        '''
        Args:
            db_handler: An object of Db.DbHandler
        '''
        FileSystemEventHandler.__init__(self)
        self._db_handler = db_handler

    def on_any_event(self, event):
        pass

    def on_created(self, event):
        logger.debug('Created %s', event.src_path)
        parent_dir_name = self._db_handler.get_remote_file_id(os.path.dirname(event.src_path))
        if event.is_directory:
            remote_id = utils.create_remote_dir(os.path.basename(event.src_path),
                                                parent_dir_name)
        else:
            remote_id = utils.copy_local_file_to_remote(event.src_path,
                                                        parent_dir_name)
        time_now = int(time.time())
        self._db_handler.insert_record(event.src_path,
                                       remote_id,
                                       time_now,
                                       time_now)

    def on_deleted(self, event):
        logger.debug('Deleted %s', event.src_path)
        utils.delete_file_on_remote(self._db_handler.get_remote_file_id(event.src_path))
        self._db_handler.delete_record(event.src_path)

    def on_modified(self, event):
        logger.debug('Modified %s', event.src_path)
        if event.is_directory:
            pass  # utils.copy_dir_to_remote
        else:
            remote_id = self._db_handler.get_remote_file_id(event.src_path)
            utils.update_remote_file(remote_id,
                                     event.src_path)
            time_now = int(time.time())
            self._db_handler.update_record(event.src_path,
                                           remote_id,
                                           time_now,
                                           time_now)

    def on_moved(self, event):
        logger.debug('Moved from %s to %s', event.src_path, event.dest_path)
        utils.delete_file_on_remote(self._db_handler.get_remote_file_id(event.src_path))
        parent_dir_name = self._db_handler.get_remote_file_id(os.path.dirname(event.src_path))
        self._db_handler.delete_record(event.src_path)

        if event.is_directory:
            remote_id = utils.create_remote_dir(os.path.basename(event.src_path),
                                                parent_dir_name)
        else:
            remote_id = utils.copy_local_file_to_remote(event.dest_path, parent_dir_name)
        time_now = int(time.time())
        self._db_handler.insert_record(event.dest_path,
                                       remote_id,
                                       time_now,
                                       time_now)
