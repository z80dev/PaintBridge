// SPDX-License-Identifier: MIT
pragma solidity >=0.8.7 <0.9.0;

import {Script, console} from "forge-std/Script.sol";
import {OriginAuthorizer} from "../contracts/OriginAuthorizer.sol";

contract SetDestinationFactory is Script {
    function run() external {
        address originAuthorizer = vm.envAddress("AUTHORIZER_ADDRESS");

        address destinationFactory = vm.envAddress("BRIDGE_ADDRESS");

        vm.startBroadcast();

        OriginAuthorizer authorizer = OriginAuthorizer(payable(originAuthorizer));
        authorizer.setDestinationFactoryAddress(destinationFactory);

        vm.stopBroadcast();

        console.log("Set destination factory to:", destinationFactory);
    }
}
