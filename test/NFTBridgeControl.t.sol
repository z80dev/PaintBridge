// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import {Test, console} from "forge-std/Test.sol";
import {MockEndpoint} from "../contracts/MockEndpoint.sol";
import {NFTFactory} from "../contracts/NFTFactory.sol";
import {NFTBridgeControl} from "../contracts/NFTBridgeControl.sol";

import {IERC721Enumerable} from "../contracts/interfaces/IERC721Enumerable.sol";
import {IERC721} from "../contracts/interfaces/IERC721.sol";
import {ERC1155} from "../contracts/ERC1155.sol";
import {IManagedNFT} from "../contracts/interfaces/IManagedNFT.sol";

import {ERC2981} from "../contracts/ERC2981.sol";

contract NFTBridgeControlTest is Test {

    uint32 TEST_EID = 1;

    MockEndpoint endpoint;
    NFTFactory nftFactory;
    NFTBridgeControl bridgeControl;

    function setUp() public {
        endpoint = new MockEndpoint();
        nftFactory = new NFTFactory();
        bridgeControl = new NFTBridgeControl(address(endpoint), address(nftFactory), TEST_EID);
    }

    function test_BridgeCollection() public {
        address originalAddress = address(0x1001);
        address originalOwner = address(0x1002);
        string memory name = "Test Collection";
        string memory symbol = "TST";
        string memory baseURI = "https://test.com/";
        string memory extension = ".json";
        address royaltyRecipient = address(0x1003);
        uint256 royaltyBps = 1000;
        bool isEnumerable = false;
        address newCollection = bridgeControl.deployERC721(originalAddress, originalOwner, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps, isEnumerable);
        assertEq(bridgeControl.bridgedAddressForOriginal(originalAddress), newCollection);
        assertEq(bridgeControl.originalOwnerForCollection(newCollection), originalOwner);

        address recipient = address(0x1004);
        IManagedNFT(newCollection).mint(recipient, 1);
        assertEq(IERC721(newCollection).ownerOf(1), recipient);
    }

    function test_BridgeEnumerableCollection() public {
        address originalAddress = address(0x1001);
        address originalOwner = address(0x1002);
        string memory name = "Test Collection";
        string memory symbol = "TST";
        string memory baseURI = "https://test.com/";
        string memory extension = ".json";
        address royaltyRecipient = address(0x1003);
        uint256 royaltyBps = 1000;
        bool isEnumerable = true;
        address newCollection = bridgeControl.deployERC721(originalAddress, originalOwner, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps, isEnumerable);

        assertEq(bridgeControl.bridgedAddressForOriginal(originalAddress), newCollection);
        assertEq(bridgeControl.originalOwnerForCollection(newCollection), originalOwner);

        IERC721Enumerable enumerable = IERC721Enumerable(newCollection);
        assertEq(enumerable.supportsInterface(0x780e9d63), true);

        address recipient = address(0x1004);
        IManagedNFT(newCollection).mint(recipient, 1);
        assertEq(enumerable.totalSupply(), 1);
        assertEq(enumerable.tokenOfOwnerByIndex(recipient, 0), 1);
        assertEq(enumerable.tokenByIndex(0), 1);
    }

    function test_Bridge1155Collection() public {
        address originalAddress = address(0x1001);
        address originalOwner = address(0x1002);
        address royaltyRecipient = address(0x1003);
        uint256 royaltyBps = 1000;
        string memory uri = "https://test.com/";
        address newCollection = bridgeControl.deployERC1155(originalAddress, originalOwner, royaltyRecipient, royaltyBps, uri);
        assertEq(bridgeControl.bridgedAddressForOriginal(originalAddress), newCollection);
        assertEq(bridgeControl.originalOwnerForCollection(newCollection), originalOwner);

        address recipient = address(0x1004);
        ERC1155(newCollection).mint(recipient, 1, 1, "");
        assertEq(ERC1155(newCollection).balanceOf(recipient, 1), 1);
    }

    function test_RoyaltyPctCalculation() public {
        address originalAddress = address(0x1001);
        address originalOwner = address(0x1002);
        string memory name = "Test Collection";
        string memory symbol = "TST";
        string memory baseURI = "https://test.com/";
        string memory extension = ".json";
        address royaltyRecipient = address(0x1003);
        uint256 royaltyBps = 1000;
        bool isEnumerable = true;
        address newCollection = bridgeControl.deployERC721(originalAddress, originalOwner, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps, isEnumerable);

        uint256 ONE_ETH = 1 ether;
        uint256 expectedRoyalty = ONE_ETH / 10;
        (address recipient, uint256 royalty) = ERC2981(newCollection).royaltyInfo(1, ONE_ETH);
        assertEq(royalty, expectedRoyalty);
        assertEq(recipient, royaltyRecipient);
    }


}
