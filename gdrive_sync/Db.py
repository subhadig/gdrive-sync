import sqlite3
from gdrive_sync import utils

LOGGER = utils.create_logger(__name__)


class _Db_constants:
    FILE_MAPPING_INFO = 'file_mapping_info'
    LOCAL_PATH = 'local_path'
    REMOTE_ID = 'remote_id'
    LOCAL_MODIFICATION_DATE = 'local_modification_date' 
    REMOTE_MODIFICATION_DATE = 'remote_modification_date'


class DbHandler:
    '''
    Handler for all DB related operations.
    '''

    def __init__(self, db_file_path=None):
        self._db_file_path = db_file_path if db_file_path else '{}/gsync.db'.format(utils.get_gdrive_sync_home())

        def create_db_if_not_present(cursor):
            cursor.execute('CREATE TABLE IF NOT EXISTS {0} ({1} TEXT, {2} TEXT, {3} INTEGER, {4} INTEGER)'
                           .format(_Db_constants.FILE_MAPPING_INFO,
                                   _Db_constants.LOCAL_PATH,
                                   _Db_constants.REMOTE_ID,
                                   _Db_constants.LOCAL_MODIFICATION_DATE,
                                   _Db_constants.REMOTE_MODIFICATION_DATE))
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS {0} on {1}({2})'
                           .format('local_path_index',
                                   _Db_constants.FILE_MAPPING_INFO,
                                   _Db_constants.LOCAL_PATH))
            cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS {0} on {1}({2})'
                           .format('remote_id_index',
                                   _Db_constants.FILE_MAPPING_INFO,
                                   _Db_constants.REMOTE_ID))
        self._execute_in_transaction(create_db_if_not_present)

    def _execute_in_transaction(self, function):
        '''
        Executes the function within a transaction boundary.
        Args:
            function: A function that takes cursor as input argument and returns no value.
        '''
        try:
            connection = sqlite3.connect(self._db_file_path)
            cursor = connection.cursor()
            function(cursor)
            connection.commit()
        except Exception:
            connection.rollback()
            LOGGER.error('Unable to commit db opearation:', exc_info=True)
        finally:
            connection.close()

    def insert_record(self, 
                      local_path, 
                      remote_id, 
                      local_modification_date, 
                      remote_modification_date):
        '''
        If no record with local_path exists, inserts the inputs as a record in Db.
        Else updates the existing record.
        Args:
            local_path: 'A String'
            remote_id: 'A String'
            local_modification_date: Integer
            remote_modification_date: Integer
        '''
        def insert_function(cursor):
            cursor.execute('SELECT 1 FROM {tn} WHERE {cn1}=?'
                           .format(tn=_Db_constants.FILE_MAPPING_INFO,
                                   cn1=_Db_constants.LOCAL_PATH),
                           (local_path,))
            if len(cursor.fetchall()):
                cursor.execute('UPDATE {tn} SET {cn1}=?, {cn2}=?, {cn3}=? WHERE {cn4}=?'
                           .format(tn=_Db_constants.FILE_MAPPING_INFO,
                                   cn1=_Db_constants.REMOTE_ID,
                                   cn2=_Db_constants.LOCAL_MODIFICATION_DATE,
                                   cn3=_Db_constants.REMOTE_MODIFICATION_DATE,
                                   cn4=_Db_constants.LOCAL_PATH),
                           (remote_id,
                            local_modification_date, 
                            remote_modification_date,
                            local_path))
            else:
                cursor.execute('INSERT INTO {tn} values(?, ?, ?, ?)'
                               .format(tn=_Db_constants.FILE_MAPPING_INFO),
                               (local_path, 
                                remote_id,
                                local_modification_date, 
                                remote_modification_date))
        self._execute_in_transaction(insert_function)

    def _execute_read_function(self, function):
        '''
        Executes the function and returns the return value of the function.
        No transaction is created.
        Args:
            function: A function that takes cursor as input argument.
        Returns:
            The return value of the function
        '''
        try:
            connection = sqlite3.connect(self._db_file_path)
            cursor = connection.cursor()
            return function(cursor)
        except Exception:
            LOGGER.error('Unable to complete db opearation:', exc_info=True)
        finally:
            connection.close()

    def get_remote_file_id(self, local_path):
        '''
        Fetches the remote_file_id for the input local_path from DB.
        Args:
            local_path: 'A String'
        Returns:
            The remote_id as String if records available else None
        '''
        def read_function(cursor):
            cursor.execute('SELECT {cn1} FROM {tn} WHERE {cn2}=?'
                           .format(tn=_Db_constants.FILE_MAPPING_INFO,
                                   cn1=_Db_constants.REMOTE_ID,
                                   cn2=_Db_constants.LOCAL_PATH),
                           (local_path,))
            final_val = cursor.fetchone()
            if not final_val:
                LOGGER.warning('No record available for local_path: %s', local_path)
            else:
                return final_val[0]
        return self._execute_read_function(read_function)

    def get_local_file_path(self, remote_file_id):
        '''
        Fetches the local_file_path for the input local_path from DB.
        Args:
            remote_file_id: 'A String'
        Returns:
            The local_path as String if records available else None
        '''
        def read_function(cursor):
            cursor.execute('SELECT {cn1} FROM {tn} WHERE {cn2}=?'
                           .format(tn=_Db_constants.FILE_MAPPING_INFO,
                                   cn1=_Db_constants.LOCAL_PATH,
                                   cn2=_Db_constants.REMOTE_ID),
                           (remote_file_id,))
            final_val = cursor.fetchone()
            if not final_val:
                LOGGER.warning('No record available for remote_id: %s', remote_file_id)
            else:
                return final_val[0]
        return self._execute_read_function(read_function)
    
    def get_local_modification_date(self, local_file_path):
        '''
        Fetches the local modification date for the input local file path from Db.
        Args:
            local_file_id: 'A String'
        Returns:
            The local_modification_date as Integer if record available else None
        '''
        def read_function(cursor):
            cursor.execute('SELECT {cn1} FROM {tn} WHERE {cn2}=?'
                           .format(tn=_Db_constants.FILE_MAPPING_INFO,
                                   cn1=_Db_constants.LOCAL_MODIFICATION_DATE,
                                   cn2=_Db_constants.LOCAL_PATH),
                           (local_file_path,))
            final_val = cursor.fetchone()
            if not final_val:
                LOGGER.warning('No record available for local file path: %s', local_file_path)
            else:
                return final_val[0]
        return self._execute_read_function(read_function)
    
    def get_remote_modification_date(self, remote_file_id):
        '''
        Fetches the remote modification date for the input remote file id from Db.
        Args:
            remote_file_id: 'A String'
        Returns:
            The remote_modification_date as Integer if record available else None
        '''
        def read_function(cursor):
            cursor.execute('SELECT {cn1} FROM {tn} WHERE {cn2}=?'
                           .format(tn=_Db_constants.FILE_MAPPING_INFO,
                                   cn1=_Db_constants.REMOTE_MODIFICATION_DATE,
                                   cn2=_Db_constants.REMOTE_ID),
                           (remote_file_id,))
            final_val = cursor.fetchone()
            if not final_val:
                LOGGER.warning('No record available for remote file id: %s', remote_file_id)
            else:
                return final_val[0]
        return self._execute_read_function(read_function)
    
    def update_record(self, 
                      local_path, 
                      remote_id, 
                      local_modification_date, 
                      remote_modification_date):
        '''
        Updates an existing record with local_path in Db.
        Args:
            local_path: 'A String'
            remote_id: 'A String'
            local_modification_date: Integer
            remote_modification_date: Integer
        '''
        def update_function(cursor):
            cursor.execute('UPDATE {tn} SET {cn1}=?, {cn2}=?, {cn3}=? WHERE {cn4}=?'
                           .format(tn=_Db_constants.FILE_MAPPING_INFO,
                                   cn1=_Db_constants.REMOTE_ID,
                                   cn2=_Db_constants.LOCAL_MODIFICATION_DATE,
                                   cn3=_Db_constants.REMOTE_MODIFICATION_DATE,
                                   cn4=_Db_constants.LOCAL_PATH),
                           (remote_id,
                            local_modification_date, 
                            remote_modification_date,
                            local_path))
        self._execute_in_transaction(update_function)
    
    def delete_record(self,
                      local_path):
        '''
        Deletes a record with local_path from Db.
        Args:
            local_path: 'A String'
        '''
        def delete_function(cursor):
            cursor.execute('DELETE FROM {tn} WHERE {cn1}=?'
                           .format(tn=_Db_constants.FILE_MAPPING_INFO,
                                   cn1=_Db_constants.LOCAL_PATH),
                           (local_path,))
        self._execute_in_transaction(delete_function)