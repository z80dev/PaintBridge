// SPDX-License-Identifier: MIT
pragma solidity >=0.8.7 <0.9.0;

import {Script} from "forge-std/Script.sol";
import {OriginAuthorizer} from "../contracts/OriginAuthorizer.sol";
import {console} from "forge-std/console.sol";

contract DeployOriginAuthorizer is Script {
    address constant ENDPOINT = address(0x1a44076050125825900e736c501f859c50fE728c); // Endpoint on Fantom
    uint32 constant DESTINATION_EID = 30332; // Update with actual destination chain EID

    function run() external {
        vm.startBroadcast();

        // Deploy OriginAuthorizer
        OriginAuthorizer authorizer = new OriginAuthorizer(DESTINATION_EID, ENDPOINT);

        vm.stopBroadcast();

        // Log the deployed address
        console.log("OriginAuthorizer deployed to:", address(authorizer));
    }
}
