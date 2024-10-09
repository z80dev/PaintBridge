// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import {ERC1155Base} from "./ERC1155Base.sol";
import {LibString} from "./utils/LibString.sol";

contract ERC1155 is ERC1155Base {

    address public originalCollectionAddress;

    // admin permission stuff
    mapping(address => bool) private _minters;
    bool public mintingEnabled = true;

    string private _uri;
    string private _extension;

    // tokenURI overrides everything
    mapping(uint256 => string) private _tokenURIs;

    constructor(address originalAddress, string memory uri, string memory extension) {
        _uri = uri;
        _extension = extension;
        originalCollectionAddress = originalAddress;
        _minters[msg.sender] = true;
    }

    function setCanMint(address newMinter) external {
        require(_minters[msg.sender], "ERC1155: FORBIDDEN");
        _minters[newMinter] = true;
    }

    struct AirdropUnit {
        address to;
        uint256[] ids;
        uint256[] amounts;
    }

    function bulkAirdrop(AirdropUnit[] memory airdrops) public {
        for (uint256 i = 0; i < airdrops.length; i++) {
            _batchMint(airdrops[i].to, airdrops[i].ids, airdrops[i].amounts, "");
        }
    }

    function uri(uint256 id) public view override returns (string memory) {
        if (bytes(_tokenURIs[id]).length > 0) {
            return _tokenURIs[id];
        }
        return string(abi.encodePacked(_uri, LibString.toString(id), _extension));
    }

    function batchSetTokenURIs(uint256 startId, string[] memory uris) public {
        for (uint256 i = 0; i < uris.length; i++) {
            _tokenURIs[startId + i] = uris[i];
        }
    }
}
