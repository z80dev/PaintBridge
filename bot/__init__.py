#!/usr/bin/env python3
import logging
import requests
from ape import  project
from ape.logging import logger as ape_logger, LogLevel
from silverback import SilverbackBot
from app.nft_bridge import NFTBridge
from app.config import env_vars


# Configure logging same as tg.py
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('nft_bridge_bot.log')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

ape_logger.set_level(LogLevel.ERROR)

bot: SilverbackBot = SilverbackBot()
BRIDGE = project.SCCNFTBridge.at("0xCA0967436C2862ffB078fa422b7E3366f4836e73")

nft_bridge = NFTBridge(
    env_vars.DEPLOYER_NAME,
    env_vars.DEPLOYER_PASSWORD,
    env_vars.SOURCE_ENDPOINT_ADDRESS,
    env_vars.TARGET_ENDPOINT_ADDRESS,
    int(env_vars.EXPECTED_EID),
    env_vars.FACTORY_ADDRESS,
    env_vars.BRIDGE_CONTROL_ADDRESS,
    env_vars.AUTHORIZER_ADDRESS,
    env_vars.FLASK_ENV,
    skip_authorizer=False
)

API_IP_ADDR = "http://34.229.118.170"

def get_endpoint(addr):
    return f"{API_IP_ADDR}/api/bridge/{addr}"

def bridge_over_api(addr):
    endpoint = get_endpoint(addr)
    logger.info(f"Sending bridging request to {endpoint}")

    response = requests.get(endpoint)
    if response.status_code == 200:
        logger.info(f"Successfully bridged {addr}")
        logger.info(response.json())
    else:
        logger.error(f"Failed to bridge {addr}")
        logger.error(response.text)


@bot.on_(BRIDGE.CollectionOwnerBridgingApproved)
def handle_new_event(evt):
    addr = evt.collectionAddress
    logger.info(f"Detected bridging approval for {addr}")
    #handle_bridging(addr)
    bridge_over_api(addr)

@bot.on_(BRIDGE.AdminBridgingApproved, start_block=6610000)
def handle_admin_event(evt):
    addr = evt.collectionAddress
    logger.info(f"Detected admin bridging approval for {addr}")
    #handle_bridging(addr)
    bridge_over_api(addr)
