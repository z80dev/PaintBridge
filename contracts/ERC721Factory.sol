// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import {ERC721} from "./ERC721.sol";

contract ERC721Factory {

    mapping (address => address) public bridgedAddressForOriginal;

    function deployERC721(address originalAddress, string memory name, string memory symbol, string memory baseURI) public returns (address) {
        return address(new ERC721(name, symbol, baseURI));
    }

    function didBridge(address originalAddress) public view returns (bool) {
        return bridgedAddressForOriginal[originalAddress] != address(0);
    }

}
