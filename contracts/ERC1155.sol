// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import {ERC1155Base} from "./ERC1155Base.sol";
import {ERC2981} from "./ERC2981.sol";
import {LibString} from "./utils/LibString.sol";
import {PermissionedMintingNFT} from "./PermissionedMintingNFT.sol";
import {BridgedNFT} from "./BridgedNFT.sol";

contract ERC1155 is ERC1155Base, ERC2981, PermissionedMintingNFT, BridgedNFT {
    // tokenURI overrides everything
    mapping(uint256 => string) private _tokenURIs;

    error URINotSet();
    error BurningIsDisabled();

    event BurningDisabled();

    struct AirdropUnit {
        address to;
        uint256[] ids;
        uint256[] amounts;
        bytes data;
    }

    constructor(
        address originalAddress,
        address royaltyRecipient,
        uint256 royaltyBps
    ) ERC2981(royaltyRecipient, royaltyBps) PermissionedMintingNFT() BridgedNFT(originalAddress) {}

    function mint(address to, uint256 id, uint256 amount, bytes memory data) public mintIsOpen onlyMinter {
        _mint(to, id, amount, data);
    }

    function burn(address from, uint256 id, uint256 amount) public mintIsOpen onlyMinter {
        if (!burningEnabled) revert BurningIsDisabled();
        _burn(from, id, amount);
    }

    function disableBurning() external onlyOwner {
        burningEnabled = false;
        emit BurningDisabled();
    }

    function bulkAirdrop(AirdropUnit[] calldata airdrops) public mintIsOpen onlyMinter {
        for (uint256 i = 0; i < airdrops.length; ++i) {
            _batchMint(airdrops[i].to, airdrops[i].ids, airdrops[i].amounts, airdrops[i].data);
        }
    }

    function batchSetTokenURIs(uint256 startId, string[] calldata uris) public onlyMinter {
        for (uint256 i = 0; i < uris.length; ++i) {
            _tokenURIs[startId + i] = uris[i];
        }
    }

    function setRoyalties(address recipient, uint256 bps) external onlyOwner {
        _setRoyalties(recipient, bps);
    }

    function uri(uint256 id) public view override returns (string memory) {
        if (bytes(_tokenURIs[id]).length != 0) {
            return _tokenURIs[id];
        } else {
            revert URINotSet();
        }
    }
}
