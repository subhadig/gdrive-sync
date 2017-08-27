from gdrive_sync import utils, LocalFSEventHandler
from os import path
from watchdog import observers

logger = utils.create_logger(__name__)

class GdriveSync:
    '''
    This class is responsible for doing various drive
    specific tasks.
    '''
    
    def __init__(self):
        self._remote_file_id_dict = {}
        self._local_dir_observer_dict = {}
    
    def _process_dir_pairs(self, service, dir_pairs):
        '''
        Syncs the local and remote dirs with each other.
        Also saves the local_dir inode numbers and remote_dir_ids in the _remote_file_id_dict
        
        Args:
            service: A googleapiclient.discovery.Resource object
            dir_pairs = A Dict of local dirs and remote dirs. It can be obtained by below:
                "utils.get_user_settings()['synced_dirs']"
        '''
        for local_dir, remote_dir in dir_pairs.items():
            remote_dir_id = utils.get_remote_dir(service, 'root', remote_dir.split('/')[1:])
            self._remote_file_id_dict[utils.get_inode_no(local_dir)] = remote_dir_id
            remote_files_under_dir = utils.get_remote_files_from_dir(service, remote_dir_id)
            local_files_under_dir = utils.list_files_under_local_dir(local_dir)
            self._compare_and_sync_files(service, 
                                         remote_files_under_dir, 
                                         remote_dir_id, 
                                         local_files_under_dir, 
                                         local_dir)
    
    def _compare_and_sync_files(self, service, remote_files, remote_parent_dir_id, local_files, 
                                local_parent_dir):
        '''
        Compares the local and remote files by name and modification date
        and whichever is last modified replaces the other one with same name.
        
        It also populates the _remote_file_id_dict with inode no of the local files
        as key and id of the remote files as value
        
        TODO: If it's a directory, then the containing files are compared instead.
        
        Args:
            service: A googleapiclient.discovery.Resource object
            remote_files: A list of dicts that has the below format
                {
                'id': 'A String' that represents the id of the remote file
                'name': 'A String' that represents the name of the remote file
                'modifiedTime': 'A String' that represents the last modifiedTime 
                    of the remote file in rfc3339 format
                }
            remote_parent_dir_id: 'A String' representing the parent dir id for the remote_files
            local_files: A list of os.DirEntry
            local_parent_dir: 'A String' reprenting the parent dir for the local_files 
        '''
        remote_file_dict = {file['name']: file for file in remote_files}
        
        for each_file in local_files:
            if each_file.name in remote_file_dict:
                remote_file_modified_time = utils.convert_rfc3339_time_to_epoch(
                    remote_file_dict[each_file.name]['modifiedTime'])
                
                if remote_file_modified_time < each_file.stat().st_mtime:
                    utils.overwrite_remote_file_with_local(service, 
                                                           remote_file_dict[each_file.name]['id'], 
                                                           each_file.path)
                elif remote_file_modified_time > each_file.stat().st_mtime: 
                    utils.copy_remote_file_to_local(service, 
                                                    each_file.path, 
                                                    remote_file_dict[each_file.name]['id'])
                self._remote_file_id_dict[each_file.inode()] = remote_file_dict[each_file.name]['id']
                del remote_file_dict[each_file.name]
            else:
                self._remote_file_id_dict[each_file.inode()] = utils.copy_local_file_to_remote(each_file.path,
                                                                                               remote_parent_dir_id,
                                                                                               service)
        
        for file_name, file in remote_file_dict.items():
            inode = utils.copy_remote_file_to_local(service, 
                                            path.join(local_parent_dir, file_name), 
                                            file['id'])
            self._remote_file_id_dict[inode] =  file['id']
    
    def sync_onetime(self, synced_dirs_dict):
        '''
        Collects the local vs remote directory mappings from user directory and
        synchronizes the local and remote directories.
        
        Args:
            synced_dirs_dict: A dict comprises of local vs remote dir pairs from settings
        '''
        service = utils.get_service()
        self._process_dir_pairs(service, synced_dirs_dict)
    
    def _watch_local_dir(self, dir_to_watch):
        '''
        It listens for the given directory and if any file/directory change event happens, it syncs 
        the change with the remote. It returns the observer object after starting it. 
        It should be run after _compare_and_sync_files to populate the _remote_file_id_dict first.
        Args:
            dir_to_watch: 'A String' that represents the path to the directory to watch
        Returns:
            An object of watchdog.observers.Observer.
        '''
        event_handler = LocalFSEventHandler.LocalFSEventHandler(self._remote_file_id_dict)
        observer = observers.Observer()
        observer.schedule(event_handler, dir_to_watch, recursive=True)
        observer.start()
        return observer
    
    def start_sync(self):
        '''
        This is the method to be invoked for starting the sync. 
        
        Args:
            synced_dir_pairs: A dict comprises of local dir path in String vs 
                remote dir path in String pairs
        Returns:
            A dict of local_dir_path in String and the observer.Observer objects
        '''
        synced_dirs_from_settings = utils.get_user_settings()['synced_dirs']
        self.sync_onetime(synced_dirs_from_settings)
        for local_dir in synced_dirs_from_settings.keys():
            self._local_dir_observers[local_dir] = self._watch_local_dir(local_dir)
    
    def stop_sync(self):
        '''
        This is to stop the sync and shutdown all the observers
        '''
        for observer in self._local_dir_observer_dict.keys():
            observer.stop()