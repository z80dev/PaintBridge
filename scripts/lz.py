#!/usr/bin/env python3
import logging
import time
from ape import project, networks, accounts
from eth_abi import encode
import os
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add file handler
file_handler = logging.FileHandler('layerzero_config.log')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info("Loading environment variables")
load_dotenv()

logger.info("Setting up network contexts")
source_context = networks.fantom.opera.use_provider("node")
target_context = networks.fantom.sonic.use_provider("node")

logger.info("Loading deployer account")
deployer = accounts.load("paintbot")
deployer.set_autosign(True, " ")

# Constants
logger.debug("Setting up LayerZero constants")
SONIC_MAINNET_EID = 30332
SONIC_MAINNET_ENDPOINT = "0x6F475642a6e85809B1c36Fa62763669b1b48DD5B"
SONIC_MAINNET_RECEIVE_LIBRARY = "0xe1844c5D63a9543023008D332Bd3d2e6f1FE1043"
SONIC_MAINNET_SEND_LIBRARY = "0xC39161c743D0307EB9BCc9FEF03eeb9Dc4802de7"
SONIC_MAINNET_EXECUTOR = "0x4208D6E27538189bB48E603D6123A94b8Abe0A0b"
SONIC_MAINNET_DVN = "0x282b3386571f7f794450d5789911a9804fa346b4"

FANTOM_MAINNET_EID = 30112
FANTOM_MAINNET_ENDPOINT = "0x1a44076050125825900e736c501f859c50fE728c"
FANTOM_MAINNET_RECEIVE_LIBRARY = "0xe1Dd69A2D08dF4eA6a30a91cC061ac70F98aAbe3"
FANTOM_MAINNET_SEND_LIBRARY = "0xC17BaBeF02a937093363220b0FB57De04A535D5E"
FANTOM_MAINNET_EXECUTOR = "0x2957eBc0D2931270d4a539696514b047756b3056"
FANTOM_MAINNET_DVN = "0xe60a3959ca23a92bf5aaf992ef837ca7f828628a"

logger.info("Encoding LayerZero configs")
inner_receive_config_typestr = "(uint64,uint8,uint8,uint8,address[],address[])"
encoded_receive_config_bytes = encode([inner_receive_config_typestr], [(1, 1, 0, 0, [SONIC_MAINNET_DVN], [])])
receive_config = [{"eid": FANTOM_MAINNET_EID, "configType": 2, "config": encoded_receive_config_bytes}]

# executor send config
inner_send_config_typestr = "(uint32,address)" # (size, executor address)
encoded_send_config_bytes = encode([inner_send_config_typestr], [(10000, FANTOM_MAINNET_EXECUTOR)]) # should this be sonic executor?
# now make receive config but for the origin chain (fantom)
encoded_uln_config_bytes_fantom = encode([inner_receive_config_typestr], [(1, 1, 0, 0, [FANTOM_MAINNET_DVN], [])])
uln_config_fantom = {"eid": SONIC_MAINNET_EID, "configType": 2, "config": encoded_uln_config_bytes_fantom}
send_config = [{"eid": SONIC_MAINNET_EID, "configType": 1, "config": encoded_send_config_bytes}, uln_config_fantom]

logger.info("Loading contract addresses from environment")
FACTORY_ADDRESS = os.getenv('FACTORY_ADDRESS')
BRIDGE_CONTROL_ADDRESS = os.getenv('BRIDGE_ADDRESS')
AUTHORIZER_ADDRESS = os.getenv('AUTHORIZER_ADDRESS')

logger.info(f"Factory address: {FACTORY_ADDRESS}")
logger.info(f"Bridge control address: {BRIDGE_CONTROL_ADDRESS}")
logger.info(f"Authorizer address: {AUTHORIZER_ADDRESS}")

# Set configs
logger.info("Setting send config on source chain")
with source_context:
    endpoint = project.ILayerZeroEndpointV2.at(FANTOM_MAINNET_ENDPOINT)
    logger.debug(f"Setting send library {FANTOM_MAINNET_SEND_LIBRARY} for EID {SONIC_MAINNET_EID}")
    try:
        tx1 = endpoint.setSendLibrary(AUTHORIZER_ADDRESS, SONIC_MAINNET_EID, FANTOM_MAINNET_SEND_LIBRARY, sender=deployer)
        logger.debug(f"Send library set tx: {tx1.txn_hash}")
    except Exception as e:
        logger.error(f"Error setting send library: {e}")

    logger.debug("Setting send config")
    try:
        tx2 = endpoint.setConfig(AUTHORIZER_ADDRESS, FANTOM_MAINNET_SEND_LIBRARY, send_config, sender=deployer)
        # sleep 30 seconds to allow the transaction to be mined
        time.sleep(30)
        logger.debug(f"Send config set tx: {tx2.txn_hash}")
        logger.info("Send config completed successfully")
    except Exception as e:
        logger.error(f"Error setting send config: {e}")

logger.info("Setting receive config on target chain")
with target_context:
    endpoint = project.ILayerZeroEndpointV2.at(SONIC_MAINNET_ENDPOINT)
    # logger.debug(f"Setting receive library {SONIC_MAINNET_RECEIVE_LIBRARY} for EID {FANTOM_MAINNET_EID}")
    # tx3 = endpoint.setReceiveLibrary(BRIDGE_CONTROL_ADDRESS, FANTOM_MAINNET_EID, SONIC_MAINNET_RECEIVE_LIBRARY, 0, sender=deployer)
    # logger.debug(f"Receive library set tx: {tx3.txn_hash}")

    logger.debug("Setting receive config")
    tx4 = endpoint.setConfig(BRIDGE_CONTROL_ADDRESS, SONIC_MAINNET_RECEIVE_LIBRARY, receive_config, sender=deployer)
    logger.debug(f"Receive config set tx: {tx4.txn_hash}")
    logger.info("Receive config completed successfully")

logger.info("Setting destination factory address on source chain")
with source_context:
    auth = project.OriginAuthorizer.at(AUTHORIZER_ADDRESS)
    try:
        tx5 = auth.setDestinationFactoryAddress(BRIDGE_CONTROL_ADDRESS, sender=deployer)
        logger.debug(f"Destination factory address set tx: {tx5.txn_hash}")
        logger.info("Destination factory address set successfully")
    except Exception as e:
        logger.error(f"Error setting destination factory address: {e}")

logger.info("Setting origin authorizer on target chain")
with target_context:
    bridge = project.SCCNFTBridge.at(BRIDGE_CONTROL_ADDRESS)
    tx6 = bridge.setOriginCaller(AUTHORIZER_ADDRESS, sender=deployer)
    logger.debug(f"Origin authorizer set tx: {tx6.txn_hash}")
    logger.info("Origin authorizer set successfully")

logger.info("LayerZero configuration completed successfully")
