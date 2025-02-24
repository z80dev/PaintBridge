// SPDX-License-Identifier: MIT
pragma solidity >=0.8.7 <0.9.0;

import {Script} from "forge-std/Script.sol";
import {NFTFactory, ERC721Factory, ERC1155Factory} from "../contracts/NFTFactory.sol";
import {SCCNFTBridge} from "../contracts/SCCNFTBridge.sol";
import {console} from "forge-std/console.sol";

contract DeployScript is Script {
    address constant ENDPOINT = address(0x6F475642a6e85809B1c36Fa62763669b1b48DD5B); // Endpoint on Sonic
    uint32 constant SOURCE_EID = 30112; // Fantom Mainnet

    function run() external {
        vm.startBroadcast();

        // Deploy factories first
        ERC721Factory erc721Factory = new ERC721Factory();
        ERC1155Factory erc1155Factory = new ERC1155Factory();

        // Deploy NFTFactory with factory addresses
        NFTFactory nftFactory = new NFTFactory(address(erc721Factory), address(erc1155Factory));

        // Deploy SCCNFTBridge with the factory
        SCCNFTBridge bridgeControl = new SCCNFTBridge(ENDPOINT, address(nftFactory), SOURCE_EID);

        vm.stopBroadcast();

        // Log the deployed addresses
        console.log("NFTFactory deployed to:", address(nftFactory));
        console.log("SCCNFTBridge deployed to:", address(bridgeControl));
    }
}
