import dotenv
dotenv.load_dotenv()
import logging
from ape.logging import logger as ape_logger, LogLevel
from eth_abi import encode

from ape import networks, accounts, project

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

ape_logger.set_level(LogLevel.ERROR)

source_context = networks.fantom.sonictest.use_provider("node")
target_context = networks.fantom.sonictest.use_provider("node")
deployer = accounts.load("painter")

ZERO_ADDR = "0x0000000000000000000000000000000000000000"

FANTOM_TESTNET_EID = 40112
FANTOM_TESTNET_ENDPOINT = "0x6EDCE65403992e310A62460808c4b910D972f10f"

SONIC_TESTNET_EID = 40349
SONIC_TESTNET_ENDPOINT = "0x6C7Ab2202C98C4227C5c46f1417D81144DA716Ff"
SONIC_TESTNET_RECEIVE_LIBRARY = "0xcF1B0F4106B0324F96fEfcC31bA9498caa80701C"
SONIC_TESTNET_SEND_LIBRARY = "0xd682ECF100f6F4284138AA925348633B0611Ae21"
SONIC_TESTNET_EXECUTOR = "0x9dB9Ca3305B48F196D18082e91cB64663b13d014"

origin_authorizer = None
factory = None
bridge_control = None

inner_receive_config_typestr = "(uint64,uint8,uint8,uint8,address[],address[])"
encoded_receive_config_bytes = encode([inner_receive_config_typestr], [(1, 1, 0, 0, ["0x88b27057a9e00c5f05dda29241027aff63f9e6e0"], [])])
receive_config = [{"eid": SONIC_TESTNET_EID, "configType": 2, "config": encoded_receive_config_bytes}]

inner_send_config_typestr = "(uint32,address)"
encoded_send_config_bytes = encode([inner_send_config_typestr], [(10000, SONIC_TESTNET_EXECUTOR)])
send_config = [{"eid": SONIC_TESTNET_EID, "configType": 1, "config": encoded_send_config_bytes}, receive_config[0]]

#config_typestr = "(uint32,uint32,bytes)"
#encoded_config = encode([config_typestr], [(SONIC_TESTNET_EID, SONIC_RECEIVE_LIBRARY, encoded_receive_config)])
#print("Encoded config:", encoded_config)

def deploy_dummy_nft():
    with source_context:
        return project.ERC721.deploy(ZERO_ADDR, "DummyNFT", "DNFT", "", "", deployer, 100, sender=deployer)

def set_configs(sender, receiver):
    with source_context:
        endpoint = project.ILayerZeroEndpointV2.at(SONIC_TESTNET_ENDPOINT)
        endpoint.setSendLibrary(sender.address, SONIC_TESTNET_EID, SONIC_TESTNET_SEND_LIBRARY, sender=deployer)
        endpoint.setConfig(sender.address, SONIC_TESTNET_SEND_LIBRARY, send_config, sender=deployer)
        print("Send config set")
    with target_context:
        endpoint = project.ILayerZeroEndpointV2.at(SONIC_TESTNET_ENDPOINT)
        endpoint.setReceiveLibrary(receiver.address, SONIC_TESTNET_EID, SONIC_TESTNET_RECEIVE_LIBRARY, 0, sender=deployer)
        endpoint.setConfig(receiver.address, SONIC_TESTNET_RECEIVE_LIBRARY, receive_config, sender=deployer)
        print("Receive config set")

def main():
    with source_context:
        origin_authorizer = project.OriginAuthorizer.deploy(SONIC_TESTNET_EID, SONIC_TESTNET_ENDPOINT, sender=deployer)
        print("Origin Authorizer deployed at", origin_authorizer.address)

    with target_context:
        factory = project.NFTFactory.deploy(sender=deployer)
        bridge_control = project.NFTBridgeControl.deploy(SONIC_TESTNET_ENDPOINT, factory, sender=deployer)
        print("NFT Factory deployed at", factory.address)
        print("Bridge Control deployed at", bridge_control.address)

    with source_context:
        origin_authorizer.setDestinationFactoryAddress(bridge_control.address, sender=deployer)
        print("Destination factory address set")

    with target_context:
        bridge_control.setOriginAuthorizer(origin_authorizer.address, sender=deployer)
        print("Origin authorizer address set")

    set_configs(origin_authorizer, bridge_control)

    dummy_nft = deploy_dummy_nft()
    print("Dummy NFT deployed at", dummy_nft.address)
    with source_context:
        dummy_nft.mint(deployer, 1, sender=deployer)
        dummy_nft.mint(deployer, 2, sender=deployer)
        print("Dummy NFTs minted")

    with source_context:
        tx = origin_authorizer.authorizeCollectionBridging(dummy_nft.address, sender=deployer, value=5000000000000000000)
        print("Dummy NFT authorized")
        print("EVENTS")
        for event in tx.events:
            print(event)
