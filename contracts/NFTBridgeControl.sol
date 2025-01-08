// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import { OAppReceiver, OAppCore, Ownable, Origin, MessagingFee, ILayerZeroEndpointV2 } from "./MyOApp.sol";
import { LZControl } from './LZControl.sol';
import { INFTFactory } from "./interfaces/INFTFactory.sol";
import { IManagedNFT } from "./interfaces/IManagedNFT.sol";
import { AddressByteUtil, Byte32AddressUtil } from "./utils/Utils.sol";

contract NFTBridgeControl is LZControl {

    using AddressByteUtil for address;
    using Byte32AddressUtil for bytes32;

    struct BridgedCollectionData {
        address originalAddress;    // address on origin chain
        address originalOwner;      // owner on origin chain
        uint256 bridgedBlockNumber; // block number when bridging occured
    }

    mapping (address => address) public bridgedAddressForOriginal;
    mapping (address => address) public originalOwnerForCollection;
    mapping (address => bool) public canDeploy;
    mapping(address => bool) public bridgingApproved;
    INFTFactory public nftFactory;

    event CollectionOwnerBridgingApproved(address collectionOwner, address collectionAddress, bool approved);
    event AdminBridgingApproved(address collectionAddress, bool approved);
    event CanDeploySet(address account, bool canDeploy);

    error AlreadyBridged();
    error NotApprovedForBridging();
    error Forbidden();
    error InvalidCollectionOwner();

    constructor(address endpoint, address factory, uint32 expectedEID) LZControl(endpoint, expectedEID) {
        canDeploy[msg.sender] = true;
        nftFactory = INFTFactory(factory);
    }

    function _handlePayload(bytes calldata payload) internal returns (address) {
        address collectionAddress = abi.decode(payload, (address));
        bridgingApproved[collectionAddress] = true;
        return collectionAddress;
    }

    function _lzReceive(
        Origin calldata origin,
        bytes32 guid,
        bytes calldata payload,
        address /*_executor*/,
        bytes calldata /*_extraData*/
    ) internal override {
        _validateMessage(origin, guid);
        address collectionAddress = _handlePayload(payload);
        emit CollectionOwnerBridgingApproved(origin.sender.toAddress(), collectionAddress, true);
    }

    function adminSetBridgingApproved(address collectionAddress, bool approved) external onlyOwner {
        bridgingApproved[collectionAddress] = approved;
        emit AdminBridgingApproved(collectionAddress, approved);
    }

    function setCanDeploy(address account, bool can) public onlyOwner {
        canDeploy[account] = can;
        emit CanDeploySet(account, can);
    }

    function didBridge(address originalAddress) public view returns (bool) {
        return bridgedAddressForOriginal[originalAddress] != address(0);
    }

    function claimOwnership(address collectionAddress) public {
        if (originalOwnerForCollection[collectionAddress] != msg.sender) {
            revert InvalidCollectionOwner();
        }
        Ownable(collectionAddress).transferOwnership(msg.sender);
    }

    function deployERC721(address originalAddress,
                          address originalOwner,
                          string memory name,
                          string memory symbol,
                          string memory baseURI,
                          string memory extension,
                          address royaltyRecipient,
                          uint256 royaltyBps,
                          bool isEnumerable) public returns (address) {
        if (!canDeploy[msg.sender]) {
            revert Forbidden();
        }
        if (bridgedAddressForOriginal[originalAddress] != address(0)) {
            revert AlreadyBridged();
        }
        address newCollection;
        if (isEnumerable) {
            newCollection = nftFactory.deployERC721Enumerable(originalAddress, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps);
        } else {
            newCollection = nftFactory.deployERC721(originalAddress, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps);
        }
        IManagedNFT(newCollection).setCanMint(msg.sender);
        bridgedAddressForOriginal[originalAddress] = newCollection;
        originalOwnerForCollection[newCollection] = originalOwner;
        return newCollection;
    }

    function deployERC1155(address originalAddress,
                           address originalOwner,
                           address royaltyRecipient,
                           uint256 royaltyBps,
                           string memory uri) public returns (address) {
        if (!canDeploy[msg.sender]) {
            revert Forbidden();
        }
        if (bridgedAddressForOriginal[originalAddress] != address(0)) {
            revert AlreadyBridged();
        }
        address newCollection = nftFactory.deployERC1155(originalAddress, royaltyRecipient, royaltyBps);
        IManagedNFT(newCollection).setCanMint(msg.sender);
        bridgedAddressForOriginal[originalAddress] = newCollection;
        originalOwnerForCollection[newCollection] = originalOwner;
        return newCollection;
    }

    function withdraw() public onlyOwner {
        payable(msg.sender).transfer(address(this).balance);
    }

    fallback() external payable {
    }

}
