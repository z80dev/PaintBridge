// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

interface IManagedNFT {
    function setCanMint(address newMinter) external;
    function setAdmin(address newAdmin) external;
}
