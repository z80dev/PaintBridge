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
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Set up file handler
file_handler = logging.FileHandler('nft_bridge.log')
file_handler.setLevel(logging.DEBUG)

# Set up console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("Starting NFT Bridge!!!!")

@dataclass
class AirdropUnit:
    address: str
    token_ids: List[int]
    amounts: List[int]
    is721: bool
    data: str = ""

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
            start += 100

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
        nft_contract = project.ERC1155.at(address)
        return nft_contract.supportsInterface(ERC1155_INTERFACE_ID)

    @source_chain_context
    def get_collection_data(self, original_address: str) -> Tuple[str, str, str, bool, str]:
        """Get collection metadata from the contract."""
        nft_contract = project.ERC721.at(original_address)
        name = nft_contract.name()
        symbol = nft_contract.symbol()

        try:
            tokenURI = nft_contract.tokenURI(1)
            url_data = parse_url(tokenURI)
            if url_data is None:
                return name, symbol, "", False, ""

            base_uri, _, extension = url_data
            has_extension = bool(extension)
            return name, symbol, base_uri, has_extension, extension
        except Exception:
            return name, symbol, "", False, ""

    @source_chain_context
    def get_collection_name(self, original_address: str) -> str:
        """Get the name of the collection."""
        nft_contract = project.ERC721.at(original_address)
        try:
            return nft_contract.name()
        except Exception:
            return ""

    def get_collection_data_api(self, address: str) -> Dict:
        """Get collection data from PaintSwap API.
        
        Works with either original or bridged address.
        """
        # If this is a bridged address, get the original address
        original_address = self.get_original_address(address)
        if original_address:
            address = original_address
            
        endpoint = f"https://api.paintswap.finance/v2/collections/{address}"
        logger.info(f"Fetching collection data from {endpoint}")
        response = requests.get(endpoint, timeout=60)
        data = response.json()
        return data["collection"]

    @source_chain_context
    def get_total_supply(self, original_address: str) -> int:
        """Get the total supply of the collection."""
        nft_contract = project.ERC721.at(original_address)
        try:
            return nft_contract.totalSupply()
        except Exception:
            return 0

    @source_chain_context
    def get_token_uris_via_erc721enumerable(self, original_address: str) -> List[tuple[int, str]]:
        """Fetch token URIs for the given NFT contract."""
        nft_contract = project.ERC721Enumerable.at(original_address)
        tokenIds = []
        token_uris = []
        total_supply = nft_contract.totalSupply()

        for i in range(total_supply):
            tokenId = nft_contract.tokenByIndex(i)
            tokenIds.append(tokenId)

        for tokenId in tokenIds:
            token_uris.append(nft_contract.tokenURI(tokenId))

        return list(zip(tokenIds, token_uris))

    @target_chain_context
    def set_token_uris_from_tuples(self, target_address: str, token_uris: List[tuple[int, str]]):
        logger.info(f"Setting token URIs for {target_address}")
        bridge_control = project.SCCNFTBridge.at(self.bridge_control_address)
        txs = []

        if len(token_uris) == 0:
            print(f"Token URIs list is empty for {target_address}")
            return txs

        for (tokenId, uri) in token_uris:
            logger.debug(f"Processing URI: {uri}")
            tx = bridge_control.batchSetTokenURIs(
                target_address,
                tokenId,
                [uri],
                sender=self.deployer
            )
            txs.append(tx)

        return txs

    @target_chain_context
    def clear_bridged_storage(self, original_address: str):
        """Clear bridged storage for a collection."""
        bridge_control = project.SCCNFTBridge.at(self.bridge_control_address)
        return bridge_control.clearBridgedStorage(original_address, sender=self.deployer)

    @target_chain_context
    def set_token_uris(self, target_address: str, token_uris: List[str], start_from: Optional[int] = None) -> List:
        """Set token URIs for the bridged contract with optional start index."""
        logger.info(f"Setting token URIs for {target_address}")
        bridge_control = project.SCCNFTBridge.at(self.bridge_control_address)
        txs = []

        if len(token_uris) == 0:
            print(f"Token URIs list is empty for {target_address}")
            return txs

        # Let caller override start_from logic
        if start_from is None:
            start_from = 0
            if token_uris[0] is None:
                start_from = 1
                token_uris = token_uris[1:]

        # Build batches handling None values
        current_batch = []
        current_start = start_from

        for i, uri in enumerate(token_uris):
            logger.debug(f"Processing URI: {uri}")
            if uri is None:
                # Send current batch if we have one
                if current_batch:
                    chunk_size = 5 if len(current_batch[0]) > 50 or current_batch[0].startswith(DATA_PREFIX) else 100
                    for ch in chunk(current_batch, chunk_size):
                        logger.debug(f"Setting token URIs for {target_address} from {current_start} to {current_start + len(ch) - 1}")
                        logger.info(f"Setting token URIs for {target_address} from {current_start} to {current_start + len(ch) - 1}")
                        print(f"Setting token URIs for {target_address} from {current_start} to {current_start + len(ch) - 1}")
                        tx = bridge_control.batchSetTokenURIs(
                            target_address,
                            current_start,
                            ch,
                            sender=self.deployer
                        )
                        txs.append(tx)
                        current_start += len(ch)
                    current_batch = []
                current_start = start_from + i + 1
                logger.info(f"Set current_start to {current_start}")
            else:
                current_batch.append(uri)

        # Send final batch if exists
        if current_batch:
            chunk_size = 5 if len(current_batch[0]) > 50 or current_batch[0].startswith(DATA_PREFIX) else 100
            for ch in chunk(current_batch, chunk_size):
                logger.debug(f"Setting token URIs for {target_address} from {current_start} to {current_start + len(ch) - 1}")
                tx = bridge_control.batchSetTokenURIs(
                    target_address,
                    current_start,
                    ch,
                    sender=self.deployer
                )
                txs.append(tx)
                current_start += len(ch)

        return txs
    
    @target_chain_context
    def set_token_uris_direct(self, target_address: str, token_uris: List[str], start_from: int = 0) -> List:
        """Set token URIs directly on the NFT contract, bypassing the bridge control."""
        logger.info(f"Setting token URIs directly for {target_address}")
        txs = []
        
        if len(token_uris) == 0:
            logger.info(f"Token URIs list is empty for {target_address}")
            return txs
        
        # Determine if this is ERC721 or ERC1155
        try:
            # Try to load as ERC721 first
            nft_contract = project.ERC721.at(target_address)
            is_721 = True
        except Exception:
            # If that fails, assume it's ERC1155
            nft_contract = project.ERC1155.at(target_address)
            is_721 = False
        
        logger.info(f"Contract type: {'ERC721' if is_721 else 'ERC1155'}")
        
        # Build batches handling None values
        current_batch = []
        current_start = start_from
        
        for i, uri in enumerate(token_uris):
            logger.debug(f"Processing URI: {uri}")
            if uri is None:
                # Send current batch if we have one
                if current_batch:
                    chunk_size = 5 if len(current_batch[0]) > 50 or current_batch[0].startswith(DATA_PREFIX) else 100
                    for ch in chunk(current_batch, chunk_size):
                        logger.debug(f"Setting token URIs directly for {target_address} from {current_start} to {current_start + len(ch) - 1}")
                        if is_721:
                            # For ERC721, set URIs one by one if needed or use batch function
                            try:
                                tx = nft_contract.batchSetTokenURIs(current_start, ch, sender=self.deployer)
                                txs.append(tx)
                            except Exception as e:
                                logger.warning(f"batchSetTokenURIs failed, setting URIs individually: {str(e)}")
                                for j, uri in enumerate(ch):
                                    token_id = current_start + j
                                    logger.debug(f"Setting URI for token ID {token_id}: {uri}")
                                    tx = nft_contract.setTokenURI(token_id, uri, sender=self.deployer)
                                    txs.append(tx)
                        else:
                            # For ERC1155, use batch setting
                            tx = nft_contract.batchSetTokenURIs(current_start, ch, sender=self.deployer)
                            txs.append(tx)
                        current_start += len(ch)
                    current_batch = []
                current_start = start_from + i + 1
                logger.info(f"Set current_start to {current_start}")
            else:
                current_batch.append(uri)
        
        # Send final batch if exists
        if current_batch:
            chunk_size = 5 if len(current_batch[0]) > 50 or current_batch[0].startswith(DATA_PREFIX) else 100
            for ch in chunk(current_batch, chunk_size):
                logger.debug(f"Setting token URIs directly for {target_address} from {current_start} to {current_start + len(ch) - 1}")
                if is_721:
                    # For ERC721, set URIs one by one if needed or use batch function
                    try:
                        tx = nft_contract.batchSetTokenURIs(current_start, ch, sender=self.deployer)
                        txs.append(tx)
                    except Exception as e:
                        logger.warning(f"batchSetTokenURIs failed, setting URIs individually: {str(e)}")
                        for j, uri in enumerate(ch):
                            token_id = current_start + j
                            logger.debug(f"Setting URI for token ID {token_id}: {uri}")
                            tx = nft_contract.setTokenURI(token_id, uri, sender=self.deployer)
                            txs.append(tx)
                else:
                    # For ERC1155, use batch setting
                    tx = nft_contract.batchSetTokenURIs(current_start, ch, sender=self.deployer)
                    txs.append(tx)
                current_start += len(ch)
        
        return txs

    @target_chain_context
    def get_bridged_address(self, original_address: str) -> Optional[str]:
        """Get the bridged contract address for an original contract."""
        bridge_control = project.SCCNFTBridge.at(self.bridge_control_address)
        bridged_address = bridge_control.bridgedAddressForOriginal(original_address)
        return None if bridged_address == ZERO_ADDR else bridged_address
        
    @target_chain_context
    def get_original_address(self, bridged_address: str) -> Optional[str]:
        """Get the original contract address for a bridged contract."""
        bridge_control = project.SCCNFTBridge.at(self.bridge_control_address)
        original_address = bridge_control.originalAddressForBridged(bridged_address)
        return None if original_address == ZERO_ADDR else original_address

    def resolve_original_address(self, address: str) -> Optional[str]:
        """Resolve an address to its original address.
        
        If the address is already an original address, returns it.
        If the address is a bridged address, returns the corresponding original address.
        Returns None if no matching original address is found.
        """
        # First check if this is already an original address with a bridged version
        if self.get_bridged_address(address):
            return address
            
        # Otherwise check if this is a bridged address
        original = self.get_original_address(address)
        if original:
            return original
            
        # Neither - could be an unbridged original address or an invalid address
        return None
        
    @target_chain_context
    def is_collection_approved(self, address: str) -> bool:
        """Check if the collection is approved for bridging.
        
        Works with either original or bridged address.
        """
        original_address = self.get_original_address(address)
        if original_address:
            address = original_address
            
        bridge_control = project.SCCNFTBridge.at(self.bridge_control_address)
        return bridge_control.bridgingApproved(address)

    @target_chain_context
    def deploy_1155(
        self,
        original_address: str,
        original_owner: str,
        royalty_recipient: str,
        royalty_bps: int,
        name: str
    ):
        """Deploy a bridged ERC1155 contract."""
        bridge_control = project.SCCNFTBridge.at(self.bridge_control_address)
        return bridge_control.deployERC1155(
            original_address,
            original_owner,
            royalty_recipient,
            royalty_bps,
            name,
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

    def get_holders_via_api(self, address: str) -> Dict[str, AirdropUnit]:
        """Get token holders from PaintSwap API.
        
        Works with either original or bridged address.
        """
        # If this is a bridged address, get the original address
        original_address = self.get_original_address(address)
        if original_address:
            address = original_address
            
        num_to_skip = 0
        done = False
        holders_dict = {}

        while not done:
            url = f"https://api.paintswap.finance/v2/userNFTs?requireUser=false&collections={address}&numToSkip={num_to_skip}&numToFetch=1000&orderBy=tokenId"
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
                    # If we can't add even one item, add it anyway to avoid infinite loop
                    if len(to_return) == 0:
                        to_return.append(airdrop_units[i])
                    break
                total_this_chunk += current_length
                to_return.append(airdrop_units[i])

            if not to_return:  # Additional safety check
                break

            num_consumed += len(to_return)
            yield to_return

    @target_chain_context
    def airdrop_holders(self, bridged_address: str, holders: List[AirdropUnit]) -> List:
        """Airdrop tokens to holders."""
        bridge_control = project.SCCNFTBridge.at(self.bridge_control_address)
        is721 = holders[0].is721
        txs = []

        for item_chunk in self._chunk_airdrop_units(holders, 50):
            airdrop_units: List[AirdropUnit] = [holder.to_args() for holder in item_chunk]
            logger.info(f"Airdropping {len(airdrop_units)} units to {bridged_address}")
            logger.info(f"Units: {airdrop_units}")
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
        
    @target_chain_context
    def transfer_ownership(self, collection_address: str, new_owner: str):
        """Transfer ownership of an NFT collection to a new owner.
        
        This function directly calls the transferOwnership function on the NFT contract,
        bypassing the bridge contract. It's intended for admin use only, when the admin
        wallet owns the NFT collection directly.
        
        Args:
            collection_address: The address of the NFT collection to transfer ownership of
            new_owner: The address of the new owner
            
        Returns:
            Transaction receipt
        """
        logger.info(f"Transferring ownership of {collection_address} to {new_owner}")
        
        # Load the contract using its Ownable interface
        try:
            # Any contract with Ownable functionality will work here
            ownable_contract = project.ERC721.at(collection_address)
            
            # Verify that we are the current owner
            current_owner = ownable_contract.owner()
            if current_owner != self.deployer.address:
                logger.error(f"Cannot transfer ownership: deployer {self.deployer.address} is not the current owner {current_owner}")
                raise ValueError(f"Cannot transfer ownership: deployer is not the current owner")
                
            # Transfer ownership
            logger.info(f"Calling transferOwnership on {collection_address}")
            tx = ownable_contract.transferOwnership(new_owner, sender=self.deployer)
            logger.info(f"Ownership transferred to {new_owner}, tx: {tx.txn_hash}")
            return tx
            
        except Exception as e:
            logger.error(f"Failed to transfer ownership: {str(e)}", exc_info=True)
            raise
