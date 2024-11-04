// SPDX-License-Identifier: UNLICENSED

pragma solidity >=0.8.7 <0.9.0;

contract RoyaltyRegistry {
    struct CollectionRoyaltyInfo {
        address recipient;
        uint16 fee;
    }

    // Contract to recipient royalties
    mapping(address => CollectionRoyaltyInfo) public collectionRoyalties;
}
