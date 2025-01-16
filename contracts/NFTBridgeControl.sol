// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import { Origin } from "./MyOApp.sol";
import { Ownable } from "./Ownable.sol";
import { LZControl } from './LZControl.sol';
import { INFTFactory } from "./interfaces/INFTFactory.sol";
import { IManaged721 } from "./interfaces/IManaged721.sol";
import { IManaged1155 } from "./interfaces/IManaged1155.sol";
import { Byte32AddressUtil } from "./utils/Utils.sol";
import { ERC721 } from "./ERC721.sol";
import { ERC1155 } from "./ERC1155.sol";

contract NFTBridgeControl is LZControl {

    using Byte32AddressUtil for bytes32;

    uint256 constant THREE_MONTHS = 77760000;

    mapping (address => address) public bridgedAddressForOriginal;
    mapping (address => address) public originalAddressForBridged;
    mapping (address => address) public originalOwnerForCollection;
    mapping (address => uint256) public blockNumberBridged;
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
    error AdminPeriodExpired(uint256 bl1, uint256 bl2);

    constructor(address endpoint, address factory, uint32 expectedEID) LZControl(endpoint, expectedEID) {
        canDeploy[msg.sender] = true;
        nftFactory = INFTFactory(factory);
    }

    function _handlePayload(bytes calldata payload) internal returns (address) {
        address collectionAddress = abi.decode(payload, (address));
        bridgingApproved[collectionAddress] = true;
        return collectionAddress;
    }

    function _checkBridgedWithin3Months(address collectionAddress) internal {
        address originalAddress = originalAddressForBridged[collectionAddress];
        if (block.number - blockNumberBridged[originalAddress] > THREE_MONTHS) {
            revert AdminPeriodExpired(block.number, blockNumberBridged[collectionAddress]);
        }
    }

    modifier onlyAdminDuringAdminPeriod(address collectionAddress) {
        _checkOwner();
        _checkBridgedWithin3Months(collectionAddress);
        _;
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
        bridgedAddressForOriginal[originalAddress] = newCollection;
        originalAddressForBridged[newCollection] = originalAddress;
        blockNumberBridged[originalAddress] = block.number;
        originalOwnerForCollection[newCollection] = originalOwner;
        ERC721(newCollection).setCanMint(address(this), true);
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
        bridgedAddressForOriginal[originalAddress] = newCollection;
        originalAddressForBridged[newCollection] = originalAddress;
        blockNumberBridged[originalAddress] = block.number;
        originalOwnerForCollection[newCollection] = originalOwner;
        ERC1155(newCollection).setCanMint(address(this), true);
        return newCollection;
    }

    function mint721(address collection, address to, uint256 id) public onlyAdminDuringAdminPeriod(collection) {
        IManaged721(collection).mint(to, id);
    }

    function mint1155(address collection, address to, uint256 id, uint256 amount, bytes memory data) public onlyAdminDuringAdminPeriod(collection) {
        IManaged1155(collection).mint(to, id, amount, data);
    }

    function airdrop721(address collection, ERC721.AirdropUnit[] calldata airdropUnits) public onlyAdminDuringAdminPeriod(collection) {
        ERC721(collection).bulkAirdrop(airdropUnits);
    }

    function airdrop1155(address collection, ERC1155.AirdropUnit[] calldata airdropUnits) public onlyAdminDuringAdminPeriod(collection) {
        ERC1155(collection).bulkAirdrop(airdropUnits);
    }

    function batchSetTokenURIs(address collection, uint256 startId, string[] calldata uris) public onlyAdminDuringAdminPeriod(collection) {
        ERC1155(collection).batchSetTokenURIs(startId, uris);
    }

    function setBaseURI(address collection, string memory baseURI) public onlyAdminDuringAdminPeriod(collection) {
        ERC721(collection).setBaseURI(baseURI);
    }

    function setRoyalties(address collection, address recipient, uint256 bps) public onlyAdminDuringAdminPeriod(collection) {
        ERC721(collection).setRoyalties(recipient, bps);
    }


    function withdraw() public onlyOwner {
        payable(msg.sender).transfer(address(this).balance);
    }


    fallback() external payable {
    }

}
