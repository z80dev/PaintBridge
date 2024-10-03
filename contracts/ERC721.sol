// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import {ERC721Base} from "./ERC721Base.sol";
import {LibString} from "./utils/LibString.sol";

contract ERC721 is ERC721Base {

    string private _name;
    string private _symbol;
    string private _baseURI;

    constructor(string memory name, string memory symbol, string memory baseURI) {
        _name = name;
        _symbol = symbol;
        _baseURI = baseURI;
    }

    function name() public override view returns (string memory) {
        return _name;
    }

    function symbol() public override view returns (string memory) {
        return _symbol;
    }

    function tokenURI(uint256 tokenId) public override view returns (string memory) {
        require(_exists(tokenId), "ERC721Metadata: URI query for nonexistent token");
        return string(abi.encodePacked(_baseURI, LibString.toString(tokenId)));
    }
}
