from unittest import TestCase
import os

from gdrive_sync import configs

class TestConfig(TestCase):
    
    def test_get_configs(self):
        self.assertTrue(configs.get_configs(), 'Config files should be returned')
        self.assertTrue(configs.get_configs().get('LOGGING', 'log_level'), 
                        'Log level should be returned')
        
    def test_get_config(self):
        self.assertTrue(configs.get_config('LOGGING', 'log_level'), 'Log level should be returned')