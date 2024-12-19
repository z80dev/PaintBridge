// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

abstract contract ERC2981 {

    // ERC165 bytes to add to interface array - set in parent contract
    bytes4 private constant _INTERFACE_ID_ERC2981 = 0x2a55205a;

    uint256 internal constant _SCALING_FACTOR = 10**12;
    uint256 internal _royaltyBps;
    address internal _royaltyRecipient;

    constructor(address recipient, uint256 royaltyBps) {
        _royaltyRecipient = recipient;
        _royaltyBps = royaltyBps;
    }

    // Called with the sale price to determine how much royalty
    // is owed and to whom.
    function royaltyInfo(uint256, uint256 _salePrice) external view virtual returns (address, uint256) {
        if (_royaltyBps == 0) {
            return (address(0), 0);
        }
        uint256 royaltyAmount = (_salePrice * _royaltyBps) / 10000;
        return (_royaltyRecipient, royaltyAmount);
    }

    function _setRoyalties(address recipient, uint256 bps) internal {
        _royaltyRecipient = recipient;
        _royaltyBps = bps;
        emit RoyaltiesSet(recipient, bps);
    }

    event RoyaltiesSet(address receiver, uint256 bps);
}
