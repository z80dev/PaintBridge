// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

/**
 * @title BridgedNFT
 * @dev Base contract for NFTs that are bridged from another chain
 */
abstract contract BridgedNFT {
    // The address of the original collection on the source chain
    address public immutable originalCollectionAddress;

    constructor(address originalAddress) {
        originalCollectionAddress = originalAddress;
    }
}
