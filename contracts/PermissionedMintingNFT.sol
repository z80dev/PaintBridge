// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import {Ownable} from "./Ownable.sol";

/**
 * @title PermissionedMintingNFT
 * @dev Base contract for NFT collections with permissioned minting functionality
 */
abstract contract PermissionedMintingNFT is Ownable {
    // Mapping of addresses allowed to mint
    mapping(address => bool) private _minters;

    // Global minting enabled flag
    bool public mintingEnabled = true;

    // Events
    event MintRightsGranted(address indexed minter);
    event MintRightsRevoked(address indexed minter);

    // Custom errors
    error NotMinter();
    error MintClosed();

    constructor() Ownable(msg.sender) {}

    // Modifiers
    modifier mintIsOpen() {
        if (!mintingEnabled) {
            revert MintClosed();
        }
        _;
    }

    modifier onlyMinter() {
        if (!_minters[msg.sender] && owner() != msg.sender) {
            revert NotMinter();
        }
        _;
    }

    // Minter management functions
    function setCanMint(address newMinter, bool canMint) external onlyOwner {
        _minters[newMinter] = canMint;
        emit MintRightsGranted(newMinter);
    }

    function renounceMintingRights() external {
        if (!_minters[msg.sender]) {
            revert NotMinter();
        }
        _minters[msg.sender] = false;
        emit MintRightsRevoked(msg.sender);
    }

    function closeMinting() external onlyOwner {
        mintingEnabled = false;
    }

    // Internal helper
    function _isMinter(address account) internal view returns (bool) {
        return _minters[account] || account == owner();
    }
}
