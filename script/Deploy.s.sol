// SPDX-License-Identifier: MIT
pragma solidity >=0.8.7 <0.9.0;

import {Script} from "forge-std/Script.sol";
import {NFTFactory} from "../contracts/NFTFactory.sol";
import {NFTBridgeControl} from "../contracts/NFTBridgeControl.sol";

contract DeployScript is Script {
    address constant ENDPOINT = address(0x6F475642a6e85809B1c36Fa62763669b1b48DD5B); // Endpoint on Sonic
    uint32 constant SOURCE_EID = 30112; // Fantom Mainnet

    function run() external {
        vm.startBroadcast();

        // Deploy NFTFactory first
        NFTFactory nftFactory = new NFTFactory();

        // Deploy NFTBridgeControl with the factory
        NFTBridgeControl bridgeControl = new NFTBridgeControl(
            ENDPOINT,
            address(nftFactory),
            SOURCE_EID
        );

        vm.stopBroadcast();

        // Log the deployed addresses
        console.log("NFTFactory deployed to:", address(nftFactory));
        console.log("NFTBridgeControl deployed to:", address(bridgeControl));
    }
}
