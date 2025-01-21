#!/usr/bin/env python3

from dataclasses import dataclass
import os
import requests
import logging
from typing import List, Dict, Tuple, Optional

from ape import Contract, accounts, project
from ape_ethereum import multicall

from .utils import chunk, source_chain_context, target_chain_context, parse_url
from .constants import (
    ROYALTY_REGISTRY_ADDRESS,
    ZERO_ADDR,
    DATA_PREFIX,
    ERC1155_INTERFACE_ID,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('NFTBridge')
logger.setLevel(logging.DEBUG)

@dataclass
class AirdropUnit:
    address: str
    token_ids: List[int]
    amounts: List[int]
    is721: bool
    data: Optional[str] = None

    def to_args(self):
        if self.is721:
            return (self.address, self.token_ids)
        else:
            return (self.address, self.token_ids, self.amounts, self.data)

class NFTBridge:
    def __init__(
        self,
        deployer_account_id: str,
        deployer_password: str,
        source_endpoint: str,
        target_endpoint: str,
        expected_eid: int,
        factory_address: Optional[str] = None,
        bridge_control_address: Optional[str] = None,
        authorizer_address: Optional[str] = None,
        environment: str = "production",
        skip_authorizer: bool = False
    ):
        """
        Initialize the NFT Bridge with required addresses and deployment parameters.

        Args:
            deployer_account_id: The account ID for deployment
            deployer_password: Password for the deployer account
            source_endpoint: Source chain endpoint address
            target_endpoint: Target chain endpoint address
            factory_address: Optional NFT factory address
            bridge_control_address: Optional bridge control contract address
            authorizer_address: Optional authorizer contract address
            environment: Environment type (development, production)
        """
        self.environment = environment
        self.deployer = accounts.load(deployer_account_id)
        self.deployer.set_autosign(True, deployer_password)

        self.source_endpoint = source_endpoint
        self.target_endpoint = target_endpoint

        # Initialize contracts
        if not factory_address:
            self.factory_address = self._deploy_factory()
        else:
            self.factory_address = factory_address
        if not bridge_control_address:
            self.bridge_control_address = self._deploy_bridge_control(expected_eid)
        else:
            self.bridge_control_address = bridge_control_address

        if not authorizer_address and not skip_authorizer:
            self.authorizer_address = self._deploy_authorizer()
        else:
            self.authorizer_address = authorizer_address

    @target_chain_context
    def _deploy_factory(self) -> str:
        factory = project.NFTFactory.deploy(sender=self.deployer)
        return factory.address

    @target_chain_context
    def _deploy_bridge_control(self, expected_eid) -> str:
        """Deploy or return existing bridge control contract."""
        bridge_control = project.SCCNFTBridge.deploy(
            self.target_endpoint,
            self.factory_address,
            expected_eid,
            sender=self.deployer
        )
        return bridge_control.address

    @source_chain_context
    def _deploy_authorizer(self) -> str:
        """Deploy or return existing authorizer contract."""
        authorizer = project.OriginAuthorizer.deploy(
            self.source_endpoint,
            sender=self.deployer
        )
        return authorizer.address

    @source_chain_context
    def get_token_uris(self, original_address: str, is721: bool = False) -> List[str]:
        """Fetch token URIs for the given NFT contract."""
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

        while token_uris and token_uris[-1] is None:
            token_uris.pop()
        return token_uris

    @source_chain_context
    def is_enumerable(self, original_address: str) -> bool:
        """Check if the NFT contract supports enumeration."""
        nft_contract = project.ERC721.at(original_address)
        try:
            nft_contract.totalSupply()
            return True
        except Exception:
            return False

    @source_chain_context
    def get_onchain_royalty_info(self, original_address: str) -> Tuple:
        """Get royalty information from the registry."""
        registry = project.RoyaltyRegistry.at(ROYALTY_REGISTRY_ADDRESS)
        return registry.collectionRoyalties(original_address)

    @source_chain_context
    def get_nft_royalty_info(self, original_address: str) -> Dict:
        """Get NFT-specific royalty information."""
        nft_contract = project.ERC721.at(original_address)
        ONE_ETH = 10**18
        recipient, royalty_amount = nft_contract.royaltyInfo(1, ONE_ETH)
        bps = royalty_amount // 10**14
        return {"recipient": recipient, "fee": bps}

    @source_chain_context
    def is_erc1155(self, address: str) -> bool:
        """Check if the contract implements ERC1155."""
        nft_contract = Contract(
            address,
            abi='[{"name":"supportsInterface","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function","constant":true,"inputs":[{"internalType":"bytes4","name":"interfaceId","type":"bytes4"}],"payable":false,"signature":"0x01ffc9a7"}]',
        )
        return nft_contract.supportsInterface(ERC1155_INTERFACE_ID)

    @source_chain_context
    def get_collection_data(self, original_address: str) -> Tuple[str, str, str, bool, str]:
        """Get collection metadata from the contract."""
        nft_contract = project.ERC721.at(original_address)
        name = nft_contract.name()
        symbol = nft_contract.symbol()

        tokenURI = nft_contract.tokenURI(1)
        url_data = parse_url(tokenURI)
        if url_data is None:
            return name, symbol, "", False, ""

        base_uri, _, extension = url_data
        has_extension = bool(extension)
        return name, symbol, base_uri, has_extension, extension

    def get_collection_data_api(self, original_address: str) -> Dict:
        """Get collection data from PaintSwap API."""
        endpoint = f"https://api.paintswap.finance/v2/collections/{original_address}"
        response = requests.get(endpoint, timeout=60)
        data = response.json()
        return data["collection"]

    @target_chain_context
    def set_token_uris(self, target_address: str, token_uris: List[str]) -> List:
        """Set token URIs for the bridged contract."""
        bridge_control = project.SCCNFTBridge.at(self.bridge_control_address)
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
            tx = bridge_control.batchSetTokenURIs(
                target_address,
                start_from,
                ch,
                sender=self.deployer
            )
            start_from += len(ch)
            txs.append(tx)
        return txs

    @target_chain_context
    def get_bridged_address(self, original_address: str) -> Optional[str]:
        """Get the bridged contract address for an original contract."""
        bridge_control = project.SCCNFTBridge.at(self.bridge_control_address)
        bridged_address = bridge_control.bridgedAddressForOriginal(original_address)
        return None if bridged_address == ZERO_ADDR else bridged_address

    @target_chain_context
    def deploy_1155(
        self,
        original_address: str,
        original_owner: str,
        royalty_recipient: str,
        royalty_bps: int
    ):
        """Deploy a bridged ERC1155 contract."""
        bridge_control = project.SCCNFTBridge.at(self.bridge_control_address)
        return bridge_control.deployERC1155(
            original_address,
            original_owner,
            royalty_recipient,
            royalty_bps,
            "",
            sender=self.deployer
        )

    @source_chain_context
    def get_collection_owner(self, original_address: str) -> str:
        """Get the owner of the original collection."""
        nft_contract = project.ERC721.at(original_address)
        try:
            return nft_contract.owner()
        except Exception:
            return ZERO_ADDR

    @target_chain_context
    def deploy_721(
        self,
        original_address: str,
        original_owner: str,
        name: str,
        symbol: str,
        base_uri: str,
        extension: str,
        recipient: str,
        bps: int
    ):
        """Deploy a bridged ERC721 contract."""
        bridge_control = project.SCCNFTBridge.at(self.bridge_control_address)
        logger.debug(f"bridge_control_address: {self.bridge_control_address}")
        enumerable = self.is_enumerable(original_address)
        # log all arguments
        logger.debug(f"original_address: {original_address}")
        logger.debug(f"original_owner: {original_owner}")
        logger.debug(f"name: {name}")
        logger.debug(f"symbol: {symbol}")
        logger.debug(f"base_uri: {base_uri}")
        logger.debug(f"extension: {extension}")
        logger.debug(f"recipient: {recipient}")
        logger.debug(f"bps: {bps}")
        logger.debug(f"enumerable: {enumerable}")

        # check if is approved for bridging
        approved = bridge_control.bridgingApproved(original_address)
        logger.debug(f"approved: {approved}")

        return bridge_control.deployERC721(
            original_address,
            original_owner,
            name,
            symbol,
            base_uri,
            extension,
            recipient,
            bps,
            enumerable,
            sender=self.deployer
        )

    def get_holders_via_api(self, original_address: str) -> Dict[str, AirdropUnit]:
        """Get token holders from PaintSwap API."""
        num_to_skip = 0
        done = False
        holders_dict = {}

        while not done:
            url = f"https://api.paintswap.finance/v2/userNFTs?requireUser=false&collections={original_address}&numToSkip={num_to_skip}&numToFetch=1000&orderBy=tokenId"
            response = requests.get(url, timeout=60)
            data = response.json()

            try:
                nfts = data["nfts"]
            except KeyError:
                print(f"Error fetching data: {data}")
                raise

            if len(nfts) < 1000:
                done = True

            for nft_data in nfts:
                holder = nft_data["user"]
                token_id = nft_data["tokenId"]
                amount = nft_data["amount"]
                is_erc721 = nft_data["isERC721"]

                if holder not in holders_dict:
                    holders_dict[holder] = AirdropUnit(
                        holder,
                        [token_id],
                        [amount],
                        is_erc721,
                        data="",
                    )
                else:
                    holders_dict[holder].token_ids.append(token_id)
                    holders_dict[holder].amounts.append(amount)

            num_to_skip += 1000

        return holders_dict

    @staticmethod
    def _chunk_airdrop_units(airdrop_units: List[AirdropUnit], n: int):
        """Chunk airdrop units based on token IDs."""
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

    @target_chain_context
    def airdrop_holders(self, bridged_address: str, holders: List[AirdropUnit]) -> List:
        """Airdrop tokens to holders."""
        bridge_control = project.SCCNFTBridge.at(self.bridge_control_address)
        is721 = holders[0].is721
        txs = []

        for item_chunk in self._chunk_airdrop_units(holders, 200):
            airdrop_units = [holder.to_args() for holder in item_chunk]
            if is721:
                tx = bridge_control.airdrop721(
                    bridged_address,
                    airdrop_units,
                    sender=self.deployer
                )
            else:
                tx = bridge_control.airdrop1155(
                    bridged_address,
                    airdrop_units,
                    sender=self.deployer
                )
            txs.append(tx)

        return txs

    @target_chain_context
    def admin_set_bridging_approved(self, collection_address: str, approved: bool):
        """Approve or disapprove bridging for a collection."""
        bridge_control = project.SCCNFTBridge.at(self.bridge_control_address)
        return bridge_control.adminSetBridgingApproved(collection_address, approved, sender=self.deployer)
