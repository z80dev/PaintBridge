// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import {SCCNFTBridge} from "../contracts/SCCNFTBridge.sol";
import {Origin} from "../contracts/MyOApp.sol";

contract SCCNFTBridgeHarness is SCCNFTBridge {
    constructor(address endpoint, address factory, uint32 expectedEID) SCCNFTBridge(endpoint, factory, expectedEID) {}

    function validateOrigin(Origin calldata origin) public view {
        _validateOrigin(origin);
    }

    function validateGuid(bytes32 guid) public {
        _validateGuid(guid);
    }

    function handlePayload(bytes calldata payload) public returns (address) {
        return _handlePayload(payload);
    }
}
