#!/usr/bin/env python3

from dataclasses import dataclass
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

def chunk(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


@dataclass
class AirdropUnit:
    address: str
    token_ids: list[int]
    amounts: list[int]
    is721: bool

    def to_args(self):
        if self.is721:
            return (self.address, self.token_ids)
        else:
            return (self.address, self.token_ids, self.amounts)

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

@source_chain_context
def get_token_uris(original_address):
    nft_contract = project.ERC1155.at(original_address)
    token_uris = []
    may_have_more = True
    start = 0
    while may_have_more:
        call = multicall.Call()
        for i in range(start, start + 1000):
            call.add(nft_contract.uri, i)
        print(f"Getting token URIs starting at {start}")
        results = list(call())
        if results[-1] is None:
            may_have_more = False
        token_uris.extend(results)
        start += 1000
    while token_uris[-1] is None:
        token_uris.pop()
    return token_uris

@target_chain_context
def set_token_uris(target_address, token_uris):
    nft_contract = project.ERC1155.at(target_address)
    start_from = 0
    txs = []
    if token_uris[0] is None:
        start_from = 1
        token_uris = token_uris[1:]
    for ch in chunk(token_uris, 100):
        print(f"Setting URIs for tokens {start_from} to {start_from + len(ch)}")
        tx = nft_contract.batchSetTokenURIs(start_from, ch, sender=deployer)
        start_from += len(ch)
        txs.append(tx)
    return txs

@target_chain_context
def deploy_factory_if_needed():
    factory_address = os.getenv("FACTORY_ADDRESS")
    if flask_env == "development":
        project.provider.set_balance(deployer.address, 100 * 10**18)
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
def deploy_1155(original_address):
    NFT_FACTORY = project.ERC721Factory.at(factory_address)
    tx = NFT_FACTORY.deployERC1155(original_address, sender=deployer)
    print(f"Deployed 1155 contract with original address {original_address}")
    return tx

@target_chain_context
def deploy_721(original_address, name, symbol, base_uri, extension):
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

def chunk_airdrop_units(airdrop_units: list[AirdropUnit], n):
    # chunks according to the number of token ids
    num_consumed = 0
    while num_consumed < len(airdrop_units):
        total_this_chunk = 0
        to_return = []
        for i in range(num_consumed, len(airdrop_units)):
            current_length = len(airdrop_units[i].token_ids)
            if total_this_chunk + current_length > n:
                break
            total_this_chunk += current_length
            to_return.append(airdrop_units[i])
        num_consumed += len(to_return)
        yield to_return

@source_chain_context
def get_holders(original_address):
    # NOTE: There are inefficiencies in this function. Correctness valued over performance.
    # NOTE NOTE: we're replacing this with a paintswap API call soon
    holders = []
    nft_contract = project.ERC721.at(original_address)
    may_have_more = True
    start = 0
    while may_have_more:
        call = multicall.Call()
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

# rewriting a version of get_holders_via_api that returns a dict
# with addresses as keys and lists of tokenids as values
# we were never using the dict with tokenids as keys

def get_holders_via_api_improved(original_address):
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
            if holder not in holders_dict:
                holders_dict[holder] = AirdropUnit(holder, [token_id], [amount], isERC721)
            else:
                holders_dict[holder].token_ids.append(token_id)
                holders_dict[holder].amounts.append(amount)
        num_to_skip += 1000
    return holders_dict

@target_chain_context
def airdrop_holders_improved(bridged_address: str, holders: list[AirdropUnit]):
    items = holders
    txs = []
    is721 = items[0].is721
    contract = project.ERC721 if is721 else project.ERC1155
    nft = contract.at(bridged_address)
    for item_chunk in chunk_airdrop_units(items, 500):
        airdrop_units = [holder.to_args() for holder in item_chunk]
        tx = nft.bulkAirdrop(airdrop_units, sender=deployer)
        txs.append(tx)
    return txs

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
