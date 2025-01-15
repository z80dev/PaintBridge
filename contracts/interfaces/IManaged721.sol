// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

interface IManaged721 {
    function setCanMint(address newMinter, bool canMint) external;
    function setAdmin(address newAdmin) external;
    function mint(address to, uint256 tokenId) external;
}
