// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import {ERC721} from "./ERC721.sol";

contract ERC721Factory {

    mapping (address => address) public bridgedAddressForOriginal;
    mapping (address => bool) public canDeploy;

    constructor() {
        canDeploy[msg.sender] = true;
    }

    function setCanDeploy(address account, bool can) public {
        require(canDeploy[msg.sender], "ERC721Factory: FORBIDDEN");
        canDeploy[account] = can;
    }

    function deployERC721(address originalAddress, string memory name, string memory symbol, string memory baseURI) public returns (address) {
        require(canDeploy[msg.sender], "ERC721Factory: FORBIDDEN");
        ERC721 newCollection = new ERC721(name, symbol, baseURI);
        newCollection.setCanMint(msg.sender);
        address newAddress = address(newCollection);
        bridgedAddressForOriginal[originalAddress] = newAddress;
        return newAddress;
    }

    function didBridge(address originalAddress) public view returns (bool) {
        return bridgedAddressForOriginal[originalAddress] != address(0);
    }

}
