import os
from dotenv import load_dotenv

endpoints = {
    "testnet": {
        "source": "0x1a44076050125825900e736c501f859c50fE728c",
        "target": "0x6C7Ab2202C98C4227C5c46f1417D81144DA716Ff"
    },
    "prod": {
        "source": "0x1a44076050125825900e736c501f859c50fE728c",
        "target": "0x6F475642a6e85809B1c36Fa62763669b1b48DD5B"
    }
}


class EnvVars:
    PORT: str
    FLASK_ENV: str
    DEPLOYER_NAME: str
    DEPLOYER_PASSWORD: str
    EXPECTED_EID: str

    def __init__(self):
        # Load environment variables from .env file
        dotenv_path = os.path.join(os.path.dirname(__file__), "../.env")
        load_dotenv(dotenv_path)

        # Load variables
        # mandatory
        self.PORT = os.environ.get('PORT')
        if self.PORT is None:
            raise ValueError("PORT environment variable is required")

        self.FLASK_ENV = os.environ.get('FLASK_ENV')
        if self.FLASK_ENV is None:
            raise ValueError("FLASK_ENV environment variable is required")

        self.DEPLOYER_NAME = os.environ.get('DEPLOYER_NAME')
        if self.DEPLOYER_NAME is None:
            raise ValueError("DEPLOYER_NAME environment variable is required")

        self.DEPLOYER_PASSWORD = os.environ.get('DEPLOYER_PASSWORD')
        if self.DEPLOYER_PASSWORD is None:
            raise ValueError("DEPLOYER_PASSWORD environment variable is required")

        self.EXPECTED_EID = os.environ.get('EXPECTED_EID')
        if self.EXPECTED_EID is None:
            raise ValueError("EXPECTED_EID environment variable is required")

        self.DESTINATION_EID = os.environ.get('DESTINATION_EID')
        if self.DESTINATION_EID is None:
            raise ValueError("DESTINATION_EID environment variable is required")

        # optional
        self.TG_BOT_TOKEN = os.environ.get('TG_BOT_TOKEN')
        self.SOURCE_ENDPOINT_ADDRESS = endpoints[self.FLASK_ENV]["source"]
        self.TARGET_ENDPOINT_ADDRESS = endpoints[self.FLASK_ENV]["target"]
        self.FACTORY_ADDRESS = os.environ.get('FACTORY_ADDRESS')
        self.BRIDGE_CONTROL_ADDRESS = os.environ.get('BRIDGE_CONTROL_ADDRESS')
        self.AUTHORIZER_ADDRESS = os.environ.get('AUTHORIZER_ADDRESS')

    def __getattr__(self, name):
        return os.environ.get(name)

env_vars = EnvVars()
