// SPDX-License-Identifier: MIT
pragma solidity >=0.8.7 <0.9.0;

import {Script} from "forge-std/Script.sol";
import {SCCNFTBridge} from "../contracts/SCCNFTBridge.sol";
import {console} from "forge-std/console.sol";

contract SetOriginCaller is Script {
    function run() external {
        address bridgeControl = vm.parseAddress(vm.prompt("Enter SCCNFTBridge address: "));
        address originCaller = vm.parseAddress(vm.prompt("Enter OriginAuthorizer address: "));

        vm.startBroadcast();

        SCCNFTBridge bridge = SCCNFTBridge(payable(bridgeControl));
        bridge.setOriginCaller(originCaller);

        vm.stopBroadcast();

        console.log("Set origin caller to:", originCaller);
    }
}
