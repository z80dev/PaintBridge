#!/usr/bin/env python3

import ape
from ape import accounts, project, networks
import json

# functions for interacting with NFT contracts
# this includes deployment of new ERC721 contracts and minting of tokens

deployer = accounts.load("painter")
addresses = json.load(open("addresses.json"))
factory_address = addresses["factory"]
NFT_FACTORY = project.ERC721Factory.at(factory_address)

def get_bridged_address(original_address):
    with networks.ethereum.local.use_provider("foundry"):
        return NFT_FACTORY.bridgedAddressForOriginal(original_address)
