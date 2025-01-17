import os
from dotenv import load_dotenv

class EnvVars:
    def __init__(self):
        # Load environment variables from .env file
        dotenv_path = os.path.join(os.path.dirname(__file__), "../.env")
        load_dotenv(dotenv_path)

        # Load variables
        self.PORT = os.environ.get('PORT')
        self.FLASK_ENV = os.environ.get('FLASK_ENV')
        self.DEPLOYER_NAME = os.environ.get('DEPLOYER_NAME')
        self.DEPLOYER_PASSWORD = os.environ.get('DEPLOYER_PASSWORD')
        self.TG_BOT_TOKEN = os.environ.get('TG_BOT_TOKEN')
        self.SOURCE_ENDPOINT_ADDRESS = os.environ.get('SOURCE_ENDPOINT_ADDRESS')
        self.TARGET_ENDPOINT_ADDRESS = os.environ.get('TARGET_ENDPOINT_ADDRESS')
        self.EXPECTED_EID = os.environ.get('EXPECTED_EID')
        self.FACTORY_ADDRESS = os.environ.get('FACTORY_ADDRESS')
        self.BRIDGE_CONTROL_ADDRESS = os.environ.get('BRIDGE_CONTROL_ADDRESS')
        self.AUTHORIZER_ADDRESS = os.environ.get('AUTHORIZER_ADDRESS')

    def __getattr__(self, name):
        return os.environ.get(name)

env_vars = EnvVars()
