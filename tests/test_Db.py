import os
from unittest import TestCase
import traceback
import sqlite3

os.chdir('../gdrive_sync')
from gdrive_sync import Db

class TestDbHandler(TestCase):

    def __init__(self, methodName='runTest'):
        TestCase.__init__(self, methodName)
        self._test_db_path = '/tmp/test_db'

    def setUp(self):
        TestCase.setUp(self)
        self._db_handler = Db.DbHandler(self._test_db_path)
    
    def tearDown(self):
        TestCase.tearDown(self)
        os.remove(self._test_db_path)
    
    def test_init(self):
        self.assertTrue(os.path.exists(self._test_db_path), msg='Db file not created')
        
    def test_insert_record_old(self):
        def fetch_inserted_records(cursor):
            cursor.execute('select * from {} where {}=?'.format('file_mapping_info',
                                                                'local_path'),
                           ('local_path',))
            return cursor.fetchall()
        
        #Insert first record
        self._db_handler.insert_record_old('local_path', 'remote_id', 10001)
        
        records = self._execute_db_function(fetch_inserted_records)
        self.assertEqual(1, len(records))
        self.assertEqual('remote_id', records[0][1])
        self.assertEqual(10001, records[0][2])
        
        #Insert second record with lower modification_date
        self._db_handler.insert_record_old('local_path', 'remote_id', 10000)
        
        records = self._execute_db_function(fetch_inserted_records)
        self.assertEqual(1, len(records))
        self.assertEqual('remote_id', records[0][1])
        self.assertEqual(10001, records[0][2])
        
        #Insert second record with higher modification_date
        self._db_handler.insert_record_old('local_path', 'remote_id_modified', 10002)
        
        records = self._execute_db_function(fetch_inserted_records)
        self.assertEqual(1, len(records))
        self.assertEqual('remote_id_modified', records[0][1])
        self.assertEqual(10002, records[0][2])
    
    def test_get_remote_file_id(self):
        def insert_records(cursor):
            cursor.execute('insert into {} values(?, ?, ?)'.format('file_mapping_info'),
                           ('local_path', 'remote_id', 101))
        self._execute_db_function(insert_records)
        self.assertEqual('remote_id', self._db_handler.get_remote_file_id('local_path'))
    
    def test_get_local_file_path(self):
        def insert_records(cursor):
            cursor.execute('insert into {} values(?, ?, ?)'.format('file_mapping_info'),
                           ('local_path', 'remote_id', 101))
        self._execute_db_function(insert_records)
        self.assertEqual('local_path', self._db_handler.get_local_file_path('remote_id'))
        
    
    def _execute_db_function(self, function):
        try:
            connection = sqlite3.connect(self._test_db_path)
            cursor = connection.cursor()
            return_val = function(cursor)
            connection.commit()
            return return_val
        except Exception:
            connection.rollback()
            print('Db operation failed.')
            traceback.print_exc()
        finally:
            connection.close()
    
    def test_insert_record(self):
        def fetch_inserted_records(cursor):
            cursor.execute('select * from {} where {}=?'.format('file_mapping_info',
                                                                'local_path'),
                           ('local_path',))
            return cursor.fetchall()
        self._db_handler.insert_record('local_path', 
                                       'remote_id', 
                                       10002, 
                                       102)
        records = self._execute_db_function(fetch_inserted_records)
        self.assertEqual(1, len(records))
        self.assertEqual('remote_id', records[0][1])
        self.assertEqual(10002, records[0][2])
        self.assertEqual(102, records[0][3])

    def test_get_local_modification_date(self):
        def insert_records(cursor):
            cursor.execute('insert into {} values(?, ?, ?, ?)'.format('file_mapping_info'),
                           ('local_path', 'remote_id', 101, 1001))
        self._execute_db_function(insert_records)
        self.assertEqual(101, self._db_handler.get_local_modification_date('local_path'))
        
    def test_get_remote_modification_date(self):
        def insert_records(cursor):
            cursor.execute('insert into {} values(?, ?, ?, ?)'.format('file_mapping_info'),
                           ('local_path', 'remote_id', 101, 1001))
        self._execute_db_function(insert_records)
        self.assertEqual(1001, self._db_handler.get_remote_modification_date('remote_id'))
    
    def test_update_record(self):
        def insert_records(cursor):
            cursor.execute('insert into {} values(?, ?, ?, ?)'.format('file_mapping_info'),
                           ('local_path', 'remote_id', 101, 1001))
        self._execute_db_function(insert_records)
        self._db_handler.update_record('local_path', 'remote_id_modified', 102, 1002)
        
        def fetch_updated_records(cursor):
            cursor.execute('select * from {} where {}=?'.format('file_mapping_info',
                                                                'local_path'),
                           ('local_path',))
            return cursor.fetchall()
        records = self._execute_db_function(fetch_updated_records)
        self.assertEqual(1, len(records))
        self.assertEqual('remote_id_modified', records[0][1])
        self.assertEqual(102, records[0][2])
        self.assertEqual(1002, records[0][3])