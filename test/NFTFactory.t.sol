// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import {Test} from "forge-std/Test.sol";

import {NFTFactory} from "../contracts/NFTFactory.sol";

contract NFTFactoryTest is Test {

    NFTFactory nftFactory;

    function setUp() public {
        nftFactory = new NFTFactory();
    }

}
