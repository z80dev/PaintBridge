// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import {ERC721Base} from "./ERC721Base.sol";
import {LibString} from "./utils/LibString.sol";

contract ERC721 is ERC721Base {

    // the address of the original collection on Fantom
    address public originalCollectionAddress;

    // address allowed to mint, will likely be just bridge admin address
    mapping(address => bool) private _minters;

    // NFT Metadata
    string private _name;
    string private _symbol;
    string private _baseURI;

    constructor(string memory name, string memory symbol, string memory baseURI) {
        _name = name;
        _symbol = symbol;
        _baseURI = baseURI;
        _minters[msg.sender] = true;
    }

    function name() public override view returns (string memory) {
        return _name;
    }

    function symbol() public override view returns (string memory) {
        return _symbol;
    }

    function tokenURI(uint256 tokenId) public override view returns (string memory) {
        if (!_exists(tokenId)) revert TokenDoesNotExist();
        return string(abi.encodePacked(_baseURI, LibString.toString(tokenId)));
    }

    function mint(address to, uint256 id) public {
        require(_minters[msg.sender], "ERC721: FORBIDDEN");
        _mint(to, id);
    }
}
