// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import {ERC721Base} from "./ERC721Base.sol";
import {LibString} from "./utils/LibString.sol";
import {ERC2981} from "./ERC2981.sol";
import {PermissionedMintingNFT} from "./PermissionedMintingNFT.sol";
import {BridgedNFT} from "./BridgedNFT.sol";

contract ERC721 is ERC721Base, ERC2981, PermissionedMintingNFT, BridgedNFT {
    // NFT Metadata
    string private _name;
    string private _symbol;
    string private _baseURI;
    string private _extension;
    mapping(uint256 => string) private _tokenURIs;

    // Custom errors
    error TokenExists();
    error MismatchedLengths();

    constructor(
        address originalAddress,
        string memory name,
        string memory symbol,
        string memory baseURI,
        string memory hasExtension,
        address royaltyRecipient,
        uint256 royaltyBps
    ) ERC2981(royaltyRecipient, royaltyBps) PermissionedMintingNFT() BridgedNFT(originalAddress) {
        _name = name;
        _symbol = symbol;
        _baseURI = baseURI;
        _extension = hasExtension;
    }

    function name() public view override returns (string memory) {
        return _name;
    }

    function symbol() public view override returns (string memory) {
        return _symbol;
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        if (!_exists(tokenId)) revert TokenDoesNotExist();
        if (bytes(_tokenURIs[tokenId]).length != 0) {
            return _tokenURIs[tokenId];
        }
        return string(abi.encodePacked(_baseURI, LibString.toString(tokenId), _extension));
    }

    function setBaseURI(string memory baseURI) external onlyOwner {
        _baseURI = baseURI;
    }

    function batchSetTokenURIs(uint256 startId, string[] calldata uris) public onlyOwner {
        for (uint256 i = 0; i < uris.length; ++i) {
            _tokenURIs[startId + i] = uris[i];
        }
    }

    struct AirdropUnit {
        address to;
        uint256[] ids;
    }

    function bulkAirdrop(AirdropUnit[] calldata airdropUnits) public mintIsOpen onlyMinter {
        for (uint256 i = 0; i < airdropUnits.length; ++i) {
            for (uint256 j = 0; j < airdropUnits[i].ids.length; j++) {
                uint256 id = airdropUnits[i].ids[j];
                if (_exists(id)) {
                    _burn(id);
                }
                _mint(airdropUnits[i].to, id);
            }
        }
    }

    function setRoyalties(address recipient, uint256 bps) external onlyOwner {
        _setRoyalties(recipient, bps);
    }

    function supportsInterface(bytes4 interfaceId) public view virtual override returns (bool result) {
        /// @solidity memory-safe-assembly
        assembly {
            let s := shr(224, interfaceId)
            // ERC165: 0x01ffc9a7, ERC2981: 0x2a55205a, ERC721: 0x80ac58cd
            result := or(eq(s, 0x01ffc9a7), eq(s, 0x2a55205a))
            result := or(result, eq(s, 0x80ac58cd))
        }
    }
}
