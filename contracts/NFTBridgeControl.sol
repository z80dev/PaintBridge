// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import { OAppReceiver, OAppCore, Ownable, Origin, MessagingFee } from "./MyOApp.sol";
import { INFTFactory } from "./interfaces/INFTFactory.sol";
import { IManagedNFT } from "./interfaces/IManagedNFT.sol";

contract NFTBridgeControl is OAppReceiver {

    mapping (address => address) public bridgedAddressForOriginal;
    mapping (address => address) public originalOwnerForCollection;
    mapping (address => bool) public canDeploy;
    mapping(address => bool) public bridgingApproved;
    uint32 public constant EXPECTED_EID = 30112;
    address originAuthorizerAddress;
    INFTFactory public nftFactory;

    mapping(bytes32 => bool) public messageProcessed;

    event CollectionOwnerBridgingApproved(address collectionOwner, address collectionAddress, bool approved);
    event AdminBridgingApproved(address collectionAddress, bool approved);

    error AlreadyBridged();
    error NotApprovedForBridging();
    error InvalidSender();
    error InvalidSourceEid();
    error AlreadyProcessed();
    error Forbidden();
    error InvalidCollectionOwner();

    constructor(address endpoint, address factory) OAppCore(endpoint, msg.sender) Ownable(msg.sender) {
        canDeploy[msg.sender] = true;
        nftFactory = INFTFactory(factory);
    }

    function setOriginAuthorizer(address _originAuthorizerAddress) public onlyOwner {
        originAuthorizerAddress = _originAuthorizerAddress;
    }

    function _lzReceive(
        Origin calldata origin,
        bytes32 guid,
        bytes calldata payload,
        address /*_executor*/,
        bytes calldata /*_extraData*/
    ) internal override {
        // check origin.sender and origin.eid
        address sender = address(uint160(uint256(origin.sender)));
        if (sender != originAuthorizerAddress) {
            revert InvalidSender();
        }
        if (origin.srcEid != EXPECTED_EID) {
            revert InvalidSourceEid();
        }
        if (messageProcessed[guid]) {
            revert AlreadyProcessed();
        }
        messageProcessed[guid] = true;
        // decode payload into single address
        address collectionAddress = abi.decode(payload, (address));
        bridgingApproved[collectionAddress] = true;
        emit CollectionOwnerBridgingApproved(sender, collectionAddress, true);
    }

    function adminSetBridgingApproved(address collectionAddress, bool approved) external onlyOwner {
        bridgingApproved[collectionAddress] = approved;
        emit AdminBridgingApproved(collectionAddress, approved);
    }

    function setCanDeploy(address account, bool can) public onlyOwner {
        canDeploy[account] = can;
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
            newCollection = nftFactory.deployERC721Enumerable(originalAddress, originalOwner, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps);
        } else {
            newCollection = nftFactory.deployERC721(originalAddress, originalOwner, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps);
        }
        IManagedNFT(newCollection).setCanMint(msg.sender);
        IManagedNFT(newCollection).setAdmin(msg.sender);
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
        address newCollection = nftFactory.deployERC1155(originalAddress, originalOwner, royaltyRecipient, royaltyBps, uri);
        IManagedNFT(newCollection).setCanMint(msg.sender);
        IManagedNFT(newCollection).setAdmin(msg.sender);
        bridgedAddressForOriginal[originalAddress] = newCollection;
        originalOwnerForCollection[newCollection] = originalOwner;
        return newCollection;
    }

}
