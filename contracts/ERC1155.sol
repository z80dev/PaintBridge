// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import {ERC1155Base} from "./ERC1155Base.sol";
import {ERC2981} from "./ERC2981.sol";
import {LibString} from "./utils/LibString.sol";
import {Ownable} from "./Ownable.sol";

contract ERC1155 is ERC1155Base, ERC2981, Ownable {

    address public immutable originalCollectionAddress;

    // admin permission stuff
    mapping(address => bool) private _minters;
    bool public mintingEnabled = true;

    // tokenURI overrides everything
    mapping(uint256 => string) private _tokenURIs;

    event MintRightsGranted(address indexed minter);
    event MintRightsRevoked(address indexed minter);

    constructor(address originalAddress, address royaltyRecipient, uint256 royaltyBps) ERC2981(royaltyRecipient, royaltyBps) Ownable(msg.sender) {
        originalCollectionAddress = originalAddress;
        _minters[msg.sender] = true;
    }

    function setCanMint(address newMinter) external onlyOwner {
        _minters[newMinter] = true;
        emit MintRightsGranted(newMinter);
    }

    function closeMinting() external {
        require(_minters[msg.sender], "ERC721: FORBIDDEN");
        mintingEnabled = false;
    }

    function renounceMintingRights() external {
        require(_minters[msg.sender], "!MINTER");
        _minters[msg.sender] = false;
        emit MintRightsRevoked(msg.sender);
    }

    struct AirdropUnit {
        address to;
        uint256[] ids;
        uint256[] amounts;
    }

    function bulkAirdrop(AirdropUnit[] calldata airdrops) public {
        require(_minters[msg.sender] || owner() == msg.sender, "!MINTER");
        require(mintingEnabled, "ERC1155: MINTING_CLOSED");
        for (uint256 i = 0; i < airdrops.length; ++i) {
            _batchMint(airdrops[i].to, airdrops[i].ids, airdrops[i].amounts, "");
        }
    }

    function mint(address to, uint256 id, uint256 amount, bytes memory data) public {
        require(_minters[msg.sender] || owner() == msg.sender, "!MINTER");
        require(mintingEnabled, "ERC1155: MINTING_CLOSED");
        _mint(to, id, amount, data);
    }

    function uri(uint256 id) public view override returns (string memory) {
        if (bytes(_tokenURIs[id]).length != 0) {
            return _tokenURIs[id];
        } else {
            revert("ERC1155: URI not set");
        }
    }

    function batchSetTokenURIs(uint256 startId, string[] calldata uris) public onlyOwner {
        for (uint256 i = 0; i < uris.length; ++i) {
            _tokenURIs[startId + i] = uris[i];
        }
    }

    function setRoyalties(address recipient, uint256 bps) external onlyOwner {
        _setRoyalties(recipient, bps);
    }

}
