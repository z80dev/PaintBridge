// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import {ERC721Base} from "./ERC721Base.sol";
import {LibString} from "./utils/LibString.sol";
import {ERC2981} from "./ERC2981.sol";
import {Ownable} from "./Ownable.sol";

contract ERC721 is ERC721Base, ERC2981, Ownable {

    // the address of the original collection on Fantom
    address public originalCollectionAddress;

    // address allowed to mint, will likely be just bridge admin address
    mapping(address => bool) private _admins;
    mapping(address => bool) private _minters;
    bool public mintingEnabled = true;

    // NFT Metadata
    string private _name;
    string private _symbol;
    string private _baseURI;
    string private _extension;
    mapping(uint256 => string) private _tokenURIs;

    // custom errors
    error TokenExists();
    error MismatchedLengths();

    event MintRightsGranted(address indexed minter);
    event MintRightsRevoked(address indexed minter);
    event AdminRightsGranted(address indexed admin);
    event AdminRightsRevoked(address indexed admin);

    constructor(address originalAddress,
                string memory name,
                string memory symbol,
                string memory baseURI,
                string memory hasExtension,
                address royaltyRecipient,
                uint256 royaltyBps) ERC2981(royaltyRecipient, royaltyBps) Ownable(msg.sender) {
        _name = name;
        _symbol = symbol;
        _baseURI = baseURI;
        _extension = hasExtension;
        _minters[msg.sender] = true;
        _admins[msg.sender] = true;
        originalCollectionAddress = originalAddress;
    }

    function setCanMint(address newMinter) external onlyOwner {
        _minters[newMinter] = true;
        emit MintRightsGranted(newMinter);
    }

    function renounceMintingRights() external {
        _minters[msg.sender] = false;
        emit MintRightsRevoked(msg.sender);
    }

    function closeMinting() external {
        require(_minters[msg.sender], "ERC721: FORBIDDEN");
        mintingEnabled = false;
    }

    function name() public override view returns (string memory) {
        return _name;
    }

    function symbol() public override view returns (string memory) {
        return _symbol;
    }

    function tokenURI(uint256 tokenId) public override view returns (string memory) {
        if (!_exists(tokenId)) revert TokenDoesNotExist();
        if (bytes(_tokenURIs[tokenId]).length != 0) {
            return _tokenURIs[tokenId];
        }
        return string(abi.encodePacked(_baseURI, LibString.toString(tokenId), _extension));
    }
     function setBaseURI(string memory baseURI) external onlyOwner {
        _baseURI = baseURI;
    }

    function batchSetTokenURIs(uint256 startId, string[] calldata uris) public {
        for (uint256 i = 0; i < uris.length; ++i) {
            _tokenURIs[startId + i] = uris[i];
        }
    }

    function mint(address to, uint256 id) public {
        require(_minters[msg.sender] || msg.sender == owner(), "ERC721: FORBIDDEN");
        require(mintingEnabled, "ERC721: MINTING_CLOSED");
        if (_exists(id)) revert TokenExists();
        _mint(to, id);
    }

    struct AirdropUnit {
        address to;
        uint256[] ids;
    }


    function bulkAirdrop(AirdropUnit[] calldata airdropUnits) public {
        require(_minters[msg.sender] || msg.sender == owner(), "ERC721: FORBIDDEN");
        require(mintingEnabled, "ERC721: MINTING_CLOSED");
        for (uint256 i = 0; i < airdropUnits.length; ++i) {
            for (uint256 j = 0; j < airdropUnits[i].ids.length; j++) {
                uint256 id = airdropUnits[i].ids[j];
                if (_exists(id)) revert TokenExists();
                _mint(airdropUnits[i].to, id);
            }
        }
    }

    function bulkAirdrop2(address[] calldata tos, uint256[] calldata ids) public {
        require(_minters[msg.sender] || msg.sender == owner(), "ERC721: FORBIDDEN");
        require(mintingEnabled, "ERC721: MINTING_CLOSED");
        if (tos.length != ids.length) revert MismatchedLengths();
        for (uint256 i = 0; i < tos.length; ++i) {
            _mint(tos[i], ids[i]);
        }
    }

    /* ERC165 */

    function supportsInterface(bytes4 interfaceId) public view virtual override returns (bool result) {
        /// @solidity memory-safe-assembly
        assembly {
            let s := shr(224, interfaceId)
            // ERC165: 0x01ffc9a7, ERC2981: 0x2a55205a, ERC721: 0x80ac58cd
            result := or(eq(s, 0x01ffc9a7), eq(s, 0x2a55205a))
            result := or(result, eq(s, 0x80ac58cd))
        }
    }

    function setRoyalties(address recipient, uint256 bps) external onlyOwner {
        _setRoyalties(recipient, bps);
    }

}
