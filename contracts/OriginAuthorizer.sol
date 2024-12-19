// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import { OAppSender, OAppCore, Ownable, Origin, MessagingFee } from "./MyOApp.sol";

contract OriginAuthorizer is OAppSender {

    uint32 public constant DESTINATION_EID = 40349;

    constructor(address endpoint) OAppCore(endpoint, msg.sender) Ownable(msg.sender) {}

    function setDestinationFactoryAddress(address _destinationFactoryAddress) public onlyOwner {
        bytes32 addressAsBytes32 = bytes32(uint256(uint160(_destinationFactoryAddress)));
        setPeer(DESTINATION_EID, addressAsBytes32);
    }

    function authorizeCollectionBridging(address collectionAddress) external payable {
        address collectionOwner = Ownable(collectionAddress).owner();
        require(collectionOwner == msg.sender, "!OWNER");
        bytes memory payload = abi.encode(collectionAddress);
        _lzSend(30112, payload, "", MessagingFee(msg.value, 0), payable(address(this)));
    }

}
