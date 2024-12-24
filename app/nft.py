#!/usr/bin/env python3

from dataclasses import dataclass
from ape import Contract, accounts, project
from ape_ethereum import multicall
from .utils import chunk, source_chain_context, target_chain_context, parse_url
import requests
import os

# load environment var FLASK_ENV to determine if we're in dev, test or prod
flask_env = os.getenv("FLASK_ENV")

deployer = accounts.load("painter")
deployer_password = os.getenv("DEPLOYER_PASSWORD")
deployer.set_autosign(True, deployer_password)

ROYALTY_REGISTRY_ADDRESS = "0x809D88B727c4C7024462d7955777835938F02F3B"
ZERO_ADDR = "0x0000000000000000000000000000000000000000"
DATA_PREFIX: str = "data:application/json;base64,"
ERC1155_INTERFACE_ID = "0xd9b67a26"

SOURCE_ENDPOINT_ADDRESS = os.getenv("SOURCE_ENDPOINT_ADDRESS")
TARGET_ENDPOINT_ADDRESS = os.getenv("TARGET_ENDPOINT_ADDRESS")

@target_chain_context
def deploy_factory_if_needed():
    factory_address = os.getenv("FACTORY_ADDRESS")
    if flask_env == "development":
        project.provider.set_balance(deployer.address, 100 * 10**18)
    if factory_address is None or factory_address == "":
        NFT_FACTORY = project.NFTFactory
        factory = NFT_FACTORY.deploy(sender=deployer)
        return factory.address
    else:
        return factory_address

@target_chain_context
def deploy_bridge_control_if_needed():
    bridge_control_address = os.getenv("BRIDGE_CONTROL_ADDRESS")
    factory_address = deploy_factory_if_needed()
    if bridge_control_address is None or bridge_control_address == "":
        BRIDGE_CONTROL = project.NFTBridgeControl.deploy(
            TARGET_ENDPOINT_ADDRESS, factory_address, sender=deployer
        )
        return BRIDGE_CONTROL.address
    else:
        return bridge_control_address

@source_chain_context
def deploy_authorizer_if_needed():
    authorizer_address = os.getenv("AUTHORIZER_ADDRESS")
    if authorizer_address is None or authorizer_address == "":
        AUTHORIZER = project.OriginAuthorizer.deploy(SOURCE_ENDPOINT_ADDRESS, sender=deployer)
        return AUTHORIZER.address
    else:
        return authorizer_address


factory_address = deploy_factory_if_needed()
bridge_control_address = deploy_bridge_control_if_needed()


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


@source_chain_context
def get_token_uris(original_address, is721=False):
    nft_contract = project.ERC1155.at(original_address)
    if is721:
        nft_contract = project.ERC721.at(original_address)
    token_uris = []
    may_have_more = True
    start = 0
    while may_have_more:
        call = multicall.Call()
        for i in range(start, start + 100):
            if is721:
                call.add(nft_contract.tokenURI, i)
            else:
                call.add(nft_contract.uri, i)
        results = list(call())
        if results[-1] is None:
            may_have_more = False
        token_uris.extend(results)
        start += 1000
    while len(token_uris) > 0 and token_uris[-1] is None:
        token_uris.pop()
    return token_uris

@source_chain_context
def is_enumerable(original_address):
    nft_contract = project.ERC721.at(original_address)
    try:
        nft_contract.totalSupply()
    except Exception:
        return False
    return True


@source_chain_context
def get_onchain_royalty_info(original_address):
    registry = project.RoyaltyRegistry.at(ROYALTY_REGISTRY_ADDRESS)
    return registry.collectionRoyalties(original_address)


@source_chain_context
def get_nft_royalty_info(original_address):
    nft_contract = project.ERC721.at(original_address)
    # return destination address and royalty percentage in bps
    ONE_ETH = 10**18
    (recipient, royaltyAmount) = nft_contract.royaltyInfo(1, ONE_ETH)
    bps = royaltyAmount // 10**14
    return {"recipient": recipient, "fee": bps}


@source_chain_context
def is_erc1155(address):
    nft_contract = Contract(
        address,
        abi='[{"name":"supportsInterface","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function","constant":true,"inputs":[{"internalType":"bytes4","name":"interfaceId","type":"bytes4"}],"payable":false,"signature":"0x01ffc9a7"}]',
    )
    return nft_contract.supportsInterface(ERC1155_INTERFACE_ID)


@source_chain_context
def get_collection_data(original_address):
    nft_contract = project.ERC721.at(original_address)
    name = nft_contract.name()
    symbol = nft_contract.symbol()

    # lets get the tokenURI for a single token and print it
    tokenURI: str = nft_contract.tokenURI(1)
    url_data = parse_url(tokenURI)
    if url_data is None:
        return name, symbol, "", False, ""
    (base_uri, _, extension) = url_data
    has_extension = extension != ""
    return name, symbol, base_uri, has_extension, extension

def get_collection_data_api(original_address):
    endpoint = f"https://api.paintswap.finance/v2/collections/{original_address}"
    response = requests.get(endpoint, timeout=60)
    data = response.json()
    return data["collection"]


@target_chain_context
def set_token_uris(target_address, token_uris):
    nft_contract = project.ERC1155.at(target_address)
    start_from = 0
    txs = []
    if token_uris[0] is None:
        start_from = 1
        token_uris = token_uris[1:]
    chunk_size = 100
    first_uri = token_uris[0]
    if len(first_uri) > 50 or first_uri.startswith(DATA_PREFIX):
        chunk_size = 5
    for ch in chunk(token_uris, chunk_size):
        tx = nft_contract.batchSetTokenURIs(start_from, ch, sender=deployer)
        start_from += len(ch)
        txs.append(tx)
    return txs


@target_chain_context
def get_bridged_address(original_address) -> str | None:
    BRIDGE_CONTROL = project.NFTBridgeControl.at(bridge_control_address)
    print(f"Original address: {original_address}")
    print(f"Factory address: {factory_address}")
    bridged_address = BRIDGE_CONTROL.bridgedAddressForOriginal(original_address)
    print(f"Bridged address: {bridged_address}")
    if bridged_address == ZERO_ADDR:
        return None
    return bridged_address


@target_chain_context
def deploy_1155(original_address, original_owner, royaltyRecipient, royaltyBPS):
    BRIDGE_CONTROL = project.NFTBridgeControl.at(bridge_control_address)
    tx = BRIDGE_CONTROL.deployERC1155(
        original_address, original_owner, royaltyRecipient, royaltyBPS, sender=deployer
    )
    return tx


@target_chain_context
def deploy_721(
        original_address, original_owner, name, symbol, base_uri, extension, recipient, bps
):
    BRIDGE_CONTROL = project.NFTBridgeControl.at(bridge_control_address)
    enumerable = is_enumerable(original_address)
    tx = BRIDGE_CONTROL.deployERC721Enumerable(
        original_address,
        original_owner,
        name,
        symbol,
        base_uri,
        extension,
        recipient,
        bps,
        enumerable,
        sender=deployer,
    )
    return tx


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


def get_holders_via_api(original_address):
    num_to_skip = 0
    done = False
    holders_dict = {}
    last_item = None
    while not done:
        URL = f"https://api.paintswap.finance/v2/userNFTs?requireUser=false&collections={original_address}&numToSkip={num_to_skip}&numToFetch=1000&orderBy=tokenId"
        response = requests.get(URL, timeout=60)
        data = response.json()
        # write data to file
        with open("data.json", "w") as f:
            f.write(str(data))

        try:
            data = data["nfts"]
        except KeyError:
            print(f"Error fetching data: {data}")
            raise
        if len(data) < 1000:
            done = True
        for nft_data in data:
            holder = nft_data["user"]
            token_id = nft_data["tokenId"]
            amount = nft_data["amount"]
            isERC721 = nft_data["isERC721"]
            if holder not in holders_dict:
                holders_dict[holder] = AirdropUnit(
                    holder, [token_id], [amount], isERC721
                )
            else:
                holders_dict[holder].token_ids.append(token_id)
                holders_dict[holder].amounts.append(amount)
            last_item = nft_data
        num_to_skip += 1000
    print(f"Last item: {last_item}")
    return holders_dict


@target_chain_context
def airdrop_holders(bridged_address: str, holders: list[AirdropUnit]):
    items = holders
    txs = []
    is721 = items[0].is721
    contract = project.ERC721 if is721 else project.ERC1155
    nft = contract.at(bridged_address)
    for item_chunk in chunk_airdrop_units(items, 200):
        airdrop_units = [holder.to_args() for holder in item_chunk]
        tx = nft.bulkAirdrop(airdrop_units, sender=deployer)
        txs.append(tx)
    return txs
