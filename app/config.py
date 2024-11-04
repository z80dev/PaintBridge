#!/usr/bin/env python3

import os
from dotenv import load_dotenv

# path to .env in parent directory
dotenv_path = os.path.join(os.path.dirname(__file__), '../.env')
load_dotenv(dotenv_path)

class Config:
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')

class DevelopmentConfig(Config):
    DEBUG = True

class TestnetConfig(Config):
    TESTING = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'testnet': TestnetConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    return config[os.environ.get('FLASK_ENV', 'default')]
