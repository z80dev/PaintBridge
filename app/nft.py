#!/usr/bin/env python3

import ape
from ape import Contract, accounts, project, networks
from ape_ethereum import multicall
import json
import requests
import os

# functions for interacting with NFT contracts
# this includes deployment of new ERC721 contracts and minting of tokens

deployer = accounts.load("painter")
deployer_password = os.getenv("DEPLOYER_PASSWORD")
deployer.set_autosign(True, deployer_password)

# load environment var FLASK_ENV to determine if we're in dev, test or prod
# then, we're going to create a decorator that will switch the provider based on the environment
# this is useful for testing, as we can switch between local and alchemy providers
# we're going to use this decorator in the functions below
flask_env = os.getenv("FLASK_ENV")

def target_chain_context(func):
    def wrapper(*args, **kwargs):
        if flask_env == "development":
            with networks.ethereum.local.use_provider("foundry"):
                return func(*args, **kwargs)
        elif flask_env == "testnet":
            with networks.fantom.sonictest.use_provider("node"):
                return func(*args, **kwargs)
    return wrapper

# source_chain_context is just always fantom opera
def source_chain_context(func):
    def wrapper(*args, **kwargs):
        with networks.fantom.opera.use_provider("alchemy"):
            return func(*args, **kwargs)
    return wrapper

@target_chain_context
def deploy_factory_if_needed():
    factory_address = os.getenv("FACTORY_ADDRESS")
    if factory_address is None or factory_address == "":
        print("Factory address not found in environment, deploying new factory")
        NFT_FACTORY = project.ERC721Factory
        factory = NFT_FACTORY.deploy(sender=deployer)
        print(f"Factory deployed at {factory.address}")
        return factory.address
    else:
        return factory_address

factory_address = deploy_factory_if_needed()
print(f"Using factory address {factory_address}")

@target_chain_context
def get_bridged_address(original_address):
    NFT_FACTORY = project.ERC721Factory.at(factory_address)
    return NFT_FACTORY.bridgedAddressForOriginal(original_address)

@target_chain_context
def deploy_collection(original_address, name, symbol, base_uri, extension):
        NFT_FACTORY = project.ERC721Factory.at(factory_address)
        # print args we're passing
        print(f"Deploying collection with original address {original_address}")
        print(f"Name: {name}")
        print(f"Symbol: {symbol}")
        print(f"Base URI: {base_uri}")
        print(f"Extension: {extension}")
        print(f"Sender: {deployer}")
        print(f"Sender balance: {deployer.balance}")
        tx = NFT_FACTORY.deployERC721(original_address, name, symbol, base_uri, extension, sender=deployer)
        print(f"Deployed collection with original address {original_address}")
        return tx

ERC1155_INTERFACE_ID = "0xd9b67a26"

@source_chain_context
def is_erc1155(address):
    nft_contract = Contract(address, abi='[{"name":"supportsInterface","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function","constant":true,"inputs":[{"internalType":"bytes4","name":"interfaceId","type":"bytes4"}],"payable":false,"signature":"0x01ffc9a7"}]')
    return nft_contract.supportsInterface(ERC1155_INTERFACE_ID)

@source_chain_context
def get_collection_data(original_address):
    nft_contract = project.ERC721.at(original_address)
    name = nft_contract.name()
    symbol = nft_contract.symbol()

    # lets get the tokenURI for a single token and print it
    tokenURI: str = nft_contract.tokenURI(1)
    base_uri: str = '/'.join(tokenURI.split('/')[0:-1]) + '/'
    has_extension = tokenURI.endswith('.json')
    extension = ""
    if has_extension:
        extension = tokenURI.split('.')[-1]
    return name, symbol, base_uri, has_extension, extension

def chunk(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

@source_chain_context
def get_holders(original_address):
    # NOTE: There are inefficiencies in this function. Correctness valued over performance.
    # NOTE NOTE: we're replacing this with a paintswap API call soon
    holders = []
    call = multicall.Call()
    nft_contract = project.ERC721.at(original_address)
    may_have_more = True
    start = 0
    while may_have_more:
        for i in range(start, start + 5000):
            call.add(nft_contract.ownerOf, i)
        results = list(call())
        if results[-1] is None:
            may_have_more = False
        holders.extend(results)

    # holders list will have a bunch of None values at the end, we want to remove all trailing Nones
    # we don't just filter out None because tokenId 0 is sometimes a valid token
    while holders[-1] is None:
        holders.pop()

    holders_dict = {}
    for i, holder in enumerate(holders):
        if holder is not None:
            holders_dict[i] = holder

    return holders_dict

def get_holders_via_api(original_address):
    num_to_skip = 0
    done = False
    holders_dict = {}
    while not done:
        URL = f"https://api.paintswap.finance/v2/userNFTs?requireUser=false&collections={original_address}&numToSkip={num_to_skip}&numToFetch=1000&orderBy=tokenId"
        data = requests.get(URL).json()
        data = data['nfts']
        if len(data) < 1000:
            done = True
        for nft_data in data:
            holder = nft_data['user']
            token_id = nft_data['tokenId']
            amount = nft_data['amount']
            isERC721 = nft_data['isERC721']
            if isERC721:
                holders_dict[token_id] = holder
        num_to_skip += 1000
    return holders_dict

@target_chain_context
def airdrop_holders(original_address):
    holders = get_holders_via_api(original_address)
    bridged_address = get_bridged_address(original_address)
    items = list(holders.items())
    txs = []
    # chunk the items into groups of 500
    for item_chunk in chunk(items, 500):
        tokenids_by_address = {}
        airdrop_units = []
        for tokenid, address in item_chunk:
            if address not in tokenids_by_address:
                tokenids_by_address[address] = []
            tokenids_by_address[address].append(tokenid)
        for address, tokenids in tokenids_by_address.items():
            airdrop_units.append((address, tokenids))
        nft = project.ERC721.at(bridged_address)
        tx = nft.bulkAirdrop(airdrop_units, sender=deployer)
        txs.append(tx)

    return txs
