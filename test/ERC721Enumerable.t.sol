// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import {Test, console} from "forge-std/Test.sol";
import {ERC721Enumerable} from "../contracts/ERC721Enumerable.sol";

contract ERC721EnumerableTest is Test {
    ERC721Enumerable nft;
    address royaltyRecipient = address(0x5678);
    uint256 royaltyBps = 1000;

    function setUp() public {
        nft = new ERC721Enumerable(
            address(0x1234), "name", "symbol", "baseURI", "extension", royaltyRecipient, royaltyBps
        );
    }

    function test_TotalSupply() public {
        assertEq(nft.totalSupply(), 0);
        nft.mint(address(this), 1);
        assertEq(nft.totalSupply(), 1);
        nft.mint(address(this), 2);
        assertEq(nft.totalSupply(), 2);
    }

    function test_tokenByIndex() public {
        nft.mint(address(this), 1);
        nft.mint(address(this), 2);
        assertEq(nft.tokenByIndex(0), 1);
        assertEq(nft.tokenByIndex(1), 2);
    }

    function test_tokenOfOwnerByIndex() public {
        nft.mint(address(this), 1);
        nft.mint(address(this), 2);
        assertEq(nft.tokenOfOwnerByIndex(address(this), 0), 1);
        assertEq(nft.tokenOfOwnerByIndex(address(this), 1), 2);

        // transfer token 1 to second address
        address second = address(0x4321);
        nft.transferFrom(address(this), second, 1);
        assertEq(nft.tokenOfOwnerByIndex(address(this), 0), 2);
        assertEq(nft.tokenOfOwnerByIndex(second, 0), 1);

        // transfer token 2 to second address
        nft.transferFrom(address(this), second, 2);
        assertEq(nft.tokenOfOwnerByIndex(second, 0), 1);
        assertEq(nft.tokenOfOwnerByIndex(second, 1), 2);

        // revert on invalid index
        vm.expectRevert();
        nft.tokenOfOwnerByIndex(address(this), 0);
    }
}
