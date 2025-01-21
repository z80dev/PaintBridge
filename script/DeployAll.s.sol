// SPDX-License-Identifier: MIT
pragma solidity >=0.8.7 <0.9.0;

import {Script} from "forge-std/Script.sol";
import {NFTFactory, ERC721Factory, ERC1155Factory} from "../contracts/NFTFactory.sol";
import {SCCNFTBridge} from "../contracts/SCCNFTBridge.sol";
import {OriginAuthorizer} from "../contracts/OriginAuthorizer.sol";
import {console} from "forge-std/console.sol";

contract DeployAll is Script {
    // Sonic (destination chain)
    address constant SONIC_ENDPOINT = address(0x6F475642a6e85809B1c36Fa62763669b1b48DD5B);
    // Fantom (source chain)
    address constant FANTOM_ENDPOINT = address(0x1a44076050125825900e736c501f859c50fE728c);

    uint32 constant SONIC_EID = 30332;
    uint32 constant FANTOM_EID = 30112;

    function run() external {
        // Deploy on Sonic first
        uint256 sonicFork = vm.createSelectFork(vm.rpcUrl("sonic"));
        console.log("Deploying to Sonic (Destination Chain)...");

        vm.startBroadcast();
        // Deploy factories first
        ERC721Factory erc721Factory = new ERC721Factory();
        ERC1155Factory erc1155Factory = new ERC1155Factory();

        // Deploy NFTFactory with factory addresses
        NFTFactory nftFactory = new NFTFactory(address(erc721Factory), address(erc1155Factory));

        SCCNFTBridge bridgeControl = new SCCNFTBridge(SONIC_ENDPOINT, address(nftFactory), FANTOM_EID);
        vm.stopBroadcast();

        address bridgeAddress = address(bridgeControl);
        console.log("ERC721Factory deployed to:", address(erc721Factory));
        console.log("ERC1155Factory deployed to:", address(erc1155Factory));
        console.log("NFTFactory deployed to:", address(nftFactory));
        console.log("SCCNFTBridge deployed to:", bridgeAddress);

        // Switch to Fantom
        uint256 fantomFork = vm.createSelectFork(vm.rpcUrl("fantom"));
        console.log("\nDeploying to Fantom (Source Chain)...");

        vm.startBroadcast();
        // Deploy OriginAuthorizer on Fantom
        OriginAuthorizer authorizer = new OriginAuthorizer(SONIC_EID, FANTOM_ENDPOINT);

        // Set destination factory address
        authorizer.setDestinationFactoryAddress(bridgeAddress);
        vm.stopBroadcast();

        address authorizerAddress = address(authorizer);
        console.log("OriginAuthorizer deployed to:", authorizerAddress);
        console.log("Destination factory set to:", bridgeAddress);

        // Switch back to Sonic to set origin caller
        vm.selectFork(sonicFork);
        console.log("\nSwitching back to Sonic to set origin caller...");

        vm.startBroadcast();
        bridgeControl.setOriginCaller(authorizerAddress);
        vm.stopBroadcast();

        console.log("Origin caller set to:", authorizerAddress);
    }
}
