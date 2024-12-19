// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import {ERC721} from "./ERC721.sol";
import {ERC721Enumerable} from "./ERC721Enumerable.sol";
import {ERC1155} from "./ERC1155.sol";
import { OAppReceiver, OAppCore, Ownable, Origin, MessagingFee } from "./MyOApp.sol";


contract NFTFactory is OAppReceiver {

    mapping (address => address) public bridgedAddressForOriginal;
    mapping (address => bool) public canDeploy;
    mapping(address => bool) public bridgingApproved;
    uint32 public constant EXPECTED_EID = 30112;
    address originAuthorizerAddress;

    event CollectionOwnerBridgingApproved(address collectionOwner, address collectionAddress, bool approved);
    event AdminBridgingApproved(address collectionAddress, bool approved);

    constructor(address endpoint) OAppCore(endpoint, msg.sender) Ownable(msg.sender) {
        canDeploy[msg.sender] = true;
    }

    function setOriginAuthorizer(address _originAuthorizerAddress) public onlyOwner {
        originAuthorizerAddress = _originAuthorizerAddress;
    }

    function _lzReceive(
        Origin calldata origin,
        bytes32 /*_guid*/,
        bytes calldata payload,
        address /*_executor*/,
        bytes calldata /*_extraData*/
    ) internal override {
        // check origin.sender and origin.eid
        address sender = address(uint160(uint256(origin.sender)));
        require(sender == originAuthorizerAddress, "NFTFactory: INVALID_SENDER");
        require(origin.srcEid == EXPECTED_EID, "NFTFactory: INVALID_SOURCE_EID");
        // decode payload into single address
        address collectionAddress = abi.decode(payload, (address));
        bridgingApproved[collectionAddress] = true;
        emit CollectionOwnerBridgingApproved(sender, collectionAddress, true);
    }

    function adminSetBridgingApproved(address collectionAddress, bool approved) external onlyOwner {
        bridgingApproved[collectionAddress] = approved;
        emit AdminBridgingApproved(collectionAddress, approved);
    }

    function setCanDeploy(address account, bool can) public {
        require(canDeploy[msg.sender], "NFTFactory: FORBIDDEN");
        canDeploy[account] = can;
    }

    function deployERC721(address originalAddress,
                          string memory name,
                          string memory symbol,
                          string memory baseURI,
                          string memory extension,
                          address royaltyRecipient,
                          uint256 royaltyBps) public returns (address)
    {
        require(canDeploy[msg.sender], "NFTFactory: FORBIDDEN");
        require(bridgedAddressForOriginal[originalAddress] == address(0), "NFTFactory: ALREADY_BRIDGED");
        ERC721 newCollection = new ERC721(originalAddress, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps);
        newCollection.setCanMint(msg.sender);
        newCollection.setAdmin(msg.sender);
        address newAddress = address(newCollection);
        bridgedAddressForOriginal[originalAddress] = newAddress;
        return newAddress;
    }

    function deployERC721Enumerable(address originalAddress,
                          string memory name,
                          string memory symbol,
                          string memory baseURI,
                          string memory extension,
                          address royaltyRecipient,
                          uint256 royaltyBps) public returns (address)
    {
        require(canDeploy[msg.sender], "NFTFactory: FORBIDDEN");
        require(bridgedAddressForOriginal[originalAddress] == address(0), "NFTFactory: ALREADY_BRIDGED");
        ERC721 newCollection = new ERC721Enumerable(originalAddress, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps);
        newCollection.setCanMint(msg.sender);
        newCollection.setAdmin(msg.sender);
        address newAddress = address(newCollection);
        bridgedAddressForOriginal[originalAddress] = newAddress;
        return newAddress;
    }

    function deployERC1155(address originalAddress, address royaltyRecipient, uint256 royaltyBps) public returns (address) {
        require(canDeploy[msg.sender], "NFTFactory: FORBIDDEN");
        require(bridgedAddressForOriginal[originalAddress] == address(0), "NFTFactory: ALREADY_BRIDGED");
        ERC1155 newCollection = new ERC1155(originalAddress, royaltyRecipient, royaltyBps);
        newCollection.setCanMint(msg.sender);
        newCollection.setAdmin(msg.sender);
        address newAddress = address(newCollection);
        bridgedAddressForOriginal[originalAddress] = newAddress;
        return newAddress;
    }

    function didBridge(address originalAddress) public view returns (bool) {
        return bridgedAddressForOriginal[originalAddress] != address(0);
    }

}
