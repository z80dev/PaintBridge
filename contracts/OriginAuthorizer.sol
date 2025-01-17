// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import { OAppSender, OAppCore, Ownable, Origin, MessagingFee, ILayerZeroEndpointV2 } from "./MyOApp.sol";
import { OptionsBuilder } from "./OptionsBuilder.sol";

interface IEndpointV2 {
     function setSendLibrary(
        address _oapp,
        uint32 _eid,
        address _newLib
     ) external;
}

contract OriginAuthorizer is OAppSender {

    uint32 public immutable DESTINATION_EID;

    using OptionsBuilder for bytes;

    constructor(uint32 destinationEID, address endpoint) OAppCore(endpoint, msg.sender) Ownable(msg.sender) {
        DESTINATION_EID = destinationEID;
        ILayerZeroEndpointV2(endpoint).setDelegate(msg.sender);
        DESTINATION_EID = destinationEID;
    }

    function setDestinationFactoryAddress(address _destinationFactoryAddress) public onlyOwner {
        bytes32 addressAsBytes32 = bytes32(uint256(uint160(_destinationFactoryAddress)));
        setPeer(DESTINATION_EID, addressAsBytes32);
    }

    function authorizeCollectionBridging(address collectionAddress) external payable {
        address collectionOwner = Ownable(collectionAddress).owner();
        require(collectionOwner == msg.sender, "!OWNER");
        bytes memory payload = abi.encode(collectionAddress);
        uint128 _gas = 210000;
        uint128 _value = 0;
        bytes memory options = OptionsBuilder.newOptions().addExecutorLzReceiveOption(_gas, _value);
        _lzSend(DESTINATION_EID, payload, options, MessagingFee(msg.value, 0), payable(msg.sender));
    }

    function withdraw() external onlyOwner {
        payable(msg.sender).transfer(address(this).balance);
    }

    fallback() external payable {
    }

}
