// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import {ERC1155Base} from "./ERC1155Base.sol";
import {ERC2981} from "./ERC2981.sol";
import {LibString} from "./utils/LibString.sol";

contract ERC1155 is ERC1155Base, ERC2981 {

    address public originalCollectionAddress;

    // admin permission stuff
    mapping(address => bool) private _admins;
    mapping(address => bool) private _minters;
    bool public mintingEnabled = true;

    // tokenURI overrides everything
    mapping(uint256 => string) private _tokenURIs;

    constructor(address originalAddress, address royaltyRecipient, uint256 royaltyBps) ERC2981(royaltyRecipient, royaltyBps) {
        originalCollectionAddress = originalAddress;
        _minters[msg.sender] = true;
        _admins[msg.sender] = true;
    }

    function setCanMint(address newMinter) external {
        require(_minters[msg.sender], "ERC1155: FORBIDDEN");
        _minters[newMinter] = true;
    }

    function setAdmin(address newAdmin) external {
        require(_admins[msg.sender], "ERC721: FORBIDDEN");
        _admins[newAdmin] = true;
    }

    function renounceRights() external {
        _minters[msg.sender] = false;
        _admins[msg.sender] = false;
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
        } else {
            revert("ERC1155: URI not set");
        }
    }

    function batchSetTokenURIs(uint256 startId, string[] memory uris) public {
        for (uint256 i = 0; i < uris.length; i++) {
            _tokenURIs[startId + i] = uris[i];
        }
    }

    function setRoyalties(address recipient, uint256 bps) external {
        require(_admins[msg.sender], "ERC721: FORBIDDEN");
        _setRoyalties(recipient, bps);
    }

}
