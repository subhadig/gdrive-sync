from configparser import ConfigParser
from os import path

_config = ConfigParser()
_config.read(path.join(path.dirname(__file__), '..', 'configs.ini'), 'utf-8')

def get_configs():
    '''
    Returns the complete ConfigParser object
    '''
    return _config

def get_config(section, key):
    '''
    Returns the config against the input section and key.
    '''
    return _config[section][key]