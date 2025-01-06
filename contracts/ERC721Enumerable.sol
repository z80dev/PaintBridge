// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import {ERC721} from "./ERC721.sol";

contract ERC721Enumerable is ERC721 {

    // array with all token IDs, used for enumeration
    uint256[] private _allTokens;
    // Mapping from token ID to position in the allTokens array
    mapping(uint256 => uint256) private _allTokensIndex;

    // Mapping from owner to list-as-mapping of owned token IDs
    mapping(address owner => mapping(uint256 index => uint256)) private _ownedTokens;
    // Mapping from token ID to index in the ownedTokens mapping
    mapping(uint256 tokenId => uint256) private _ownedTokensIndex;

    function totalSupply() public view returns (uint256) {
        return _allTokens.length;
    }

    function tokenByIndex(uint256 index) public view returns (uint256) {
        require(index < totalSupply(), "ERC721Enumerable: INVALID_INDEX");
        return _allTokens[index];
    }

    function tokenOfOwnerByIndex(address owner, uint256 index) public view returns (uint256) {
        require(index < balanceOf(owner), "ERC721Enumerable: INVALID_INDEX");
        return _ownedTokens[owner][index];
    }

    constructor(address originalAddress,
                string memory name,
                string memory symbol,
                string memory baseURI,
                string memory hasExtension,
                address royaltyRecipient,
                uint256 royaltyBps) ERC721(originalAddress, name, symbol, baseURI, hasExtension, royaltyRecipient, royaltyBps) {}

    function _beforeTokenTransfer(address _from, address _to, uint256 _tokenId) internal override {
        if (_from == address(0)) {
            _addTokenToAllTokensEnumeration(_tokenId);
        } else if (_from != _to){
            _removeTokenFromOwnerEnumeration(_from, _tokenId);
        }
        if (_to == address(0)) {
            _removeTokenFromAllTokensEnumeration(_tokenId);
            _removeTokenFromOwnerEnumeration(_from, _tokenId);
        } else if (_to != _from){
            _addTokenToOwnerEnumeration(_to, _tokenId);
        }
    }

    /* From OZ ERC721Enumerable */
    /**
     * @dev Private function to add a token to this extension's ownership-tracking data structures.
     * @param to address representing the new owner of the given token ID
     * @param tokenId uint256 ID of the token to be added to the tokens list of the given address
     */
    function _addTokenToOwnerEnumeration(address to, uint256 tokenId) private {
        // NOTE: Balance has not been incremented yet when this is called.
        // Because of this, we don't subtract 1 from balanceOf(to) to get the index.
        // Not only is this correct, it also prevents underflow on mint.
        // The alternative would be moving this to the _afterTokenTransfer hook,
        // but that would breack CEI (reentrancy)
        uint256 length = balanceOf(to);
        _ownedTokens[to][length] = tokenId;
        _ownedTokensIndex[tokenId] = length;
    }

    /**
     * @dev Private function to add a token to this extension's token tracking data structures.
     * @param tokenId uint256 ID of the token to be added to the tokens list
     */
    function _addTokenToAllTokensEnumeration(uint256 tokenId) private {
        _allTokensIndex[tokenId] = _allTokens.length;
        _allTokens.push(tokenId);
    }

    /**
     * @dev Private function to remove a token from this extension's ownership-tracking data structures. Note that
     * while the token is not assigned a new owner, the `_ownedTokensIndex` mapping is _not_ updated: this allows for
     * gas optimizations e.g. when performing a transfer operation (avoiding double writes).
     * This has O(1) time complexity, but alters the order of the _ownedTokens array.
     * @param from address representing the previous owner of the given token ID
     * @param tokenId uint256 ID of the token to be removed from the tokens list of the given address
     */
    function _removeTokenFromOwnerEnumeration(address from, uint256 tokenId) private {
        // To prevent a gap in from's tokens array, we store the last token in the index of the token to delete, and
        // then delete the last slot (swap and pop).

        // this decrement is safe because balanceOf has not been updated yet
        // so if a user is sending their last token, balanceOf(from) will return 1
        // and the value of lastTokenIndex will correctly be 0
        uint256 lastTokenIndex = balanceOf(from) - 1;
        uint256 tokenIndex = _ownedTokensIndex[tokenId];

        mapping(uint256 index => uint256) storage _ownedTokensByOwner = _ownedTokens[from];

        // When the token to delete is the last token, the swap operation is unnecessary
        if (tokenIndex != lastTokenIndex) {
            uint256 lastTokenId = _ownedTokensByOwner[lastTokenIndex];

            _ownedTokensByOwner[tokenIndex] = lastTokenId; // Move the last token to the slot of the to-delete token
            _ownedTokensIndex[lastTokenId] = tokenIndex; // Update the moved token's index
        }

        // This also deletes the contents at the last position of the array
        delete _ownedTokensIndex[tokenId];
        delete _ownedTokensByOwner[lastTokenIndex];
    }

    /**
     * @dev Private function to remove a token from this extension's token tracking data structures.
     * This has O(1) time complexity, but alters the order of the _allTokens array.
     * @param tokenId uint256 ID of the token to be removed from the tokens list
     */
    function _removeTokenFromAllTokensEnumeration(uint256 tokenId) private {
        // To prevent a gap in the tokens array, we store the last token in the index of the token to delete, and
        // then delete the last slot (swap and pop).

        uint256 lastTokenIndex = _allTokens.length - 1;
        uint256 tokenIndex = _allTokensIndex[tokenId];

        // When the token to delete is the last token, the swap operation is unnecessary. However, since this occurs so
        // rarely (when the last minted token is burnt) that we still do the swap here to avoid the gas cost of adding
        // an 'if' statement (like in _removeTokenFromOwnerEnumeration)
        uint256 lastTokenId = _allTokens[lastTokenIndex];

        _allTokens[tokenIndex] = lastTokenId; // Move the last token to the slot of the to-delete token
        _allTokensIndex[lastTokenId] = tokenIndex; // Update the moved token's index

        // This also deletes the contents at the last position of the array
        delete _allTokensIndex[tokenId];
        _allTokens.pop();
    }

    /* ERC165 */

    function supportsInterface(bytes4 interfaceId) public pure override returns (bool result) {
        /// @solidity memory-safe-assembly
        assembly {
            let s := shr(224, interfaceId)
            // ERC165: 0x01ffc9a7
            // ERC2981: 0x2a55205a
            result := or(eq(s, 0x01ffc9a7), eq(s, 0x2a55205a))
            // ERC721: 0x80ac58cd
            result := or(result, eq(s, 0x80ac58cd))
            // ERC721Enumerable: 0x780e9d63
            result := or(result, eq(s, 0x780e9d63))
        }
    }

}
