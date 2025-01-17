// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import {OAppReceiver, OAppCore, Ownable, Origin, MessagingFee, ILayerZeroEndpointV2} from "./MyOApp.sol";
import {AddressByteUtil, Byte32AddressUtil} from "./utils/Utils.sol";

abstract contract LZControl is OAppReceiver {
    using AddressByteUtil for address;
    using Byte32AddressUtil for bytes32;

    uint32 public immutable EXPECTED_EID;
    address originCallerAddress;

    mapping(bytes32 => bool) public messageProcessed;

    error InvalidSender();
    error InvalidSourceEid();
    error AlreadyProcessed();

    constructor(address endpoint, uint32 expectedEID) OAppCore(endpoint, msg.sender) Ownable(msg.sender) {
        ILayerZeroEndpointV2(endpoint).setDelegate(msg.sender);
        EXPECTED_EID = expectedEID;
    }

    function setOriginCaller(address _originCallerAddress) public onlyOwner {
        originCallerAddress = _originCallerAddress;
        setPeer(EXPECTED_EID, bytes32(uint256(uint160(_originCallerAddress))));
    }

    function _validateOrigin(Origin calldata origin) internal view {
        if (origin.sender.toAddress() != originCallerAddress) {
            revert InvalidSender();
        }
        if (origin.srcEid != EXPECTED_EID) {
            revert InvalidSourceEid();
        }
    }

    function _validateGuid(bytes32 guid) internal {
        if (messageProcessed[guid]) {
            revert AlreadyProcessed();
        }
        messageProcessed[guid] = true;
    }

    function _validateMessage(Origin calldata origin, bytes32 guid) internal {
        _validateOrigin(origin);
        _validateGuid(guid);
    }
}
