// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import {Test, console} from "forge-std/Test.sol";
import {MockEndpoint} from "../contracts/MockEndpoint.sol";
import {NFTFactory} from "../contracts/NFTFactory.sol";
import {NFTBridgeControl} from "../contracts/NFTBridgeControl.sol";
import {NFTBridgeControlHarness} from "./NFTBridgeControlHarness.sol";

import {IERC721Enumerable} from "../contracts/interfaces/IERC721Enumerable.sol";
import {IERC721} from "../contracts/interfaces/IERC721.sol";
import { ERC721 } from "../contracts/ERC721.sol";
import {ERC1155} from "../contracts/ERC1155.sol";
import {IManaged721} from "../contracts/interfaces/IManaged721.sol";
import {IManaged1155} from "../contracts/interfaces/IManaged1155.sol";

import {ERC2981} from "../contracts/ERC2981.sol";

import {Origin} from "../contracts/MyOApp.sol";

library AddressByteUtil {
    function toBytes32(address addr) internal pure returns (bytes32) {
        return bytes32(uint256(uint160(addr)));

    }
}

library Byte32AddressUtil {
    function toAddress(bytes32 b) internal pure returns (address) {
        return address(uint160(uint256(b)));
    }

}

contract NFTBridgeControlTest is Test {

    using AddressByteUtil for address;
    using Byte32AddressUtil for bytes32;

    uint32 TEST_EID = 1;
    bytes32 ORIGIN_SENDER = address(0xabcd).toBytes32();

    address ATTACKER = address(0x4321);

    MockEndpoint endpoint;
    NFTFactory nftFactory;
    NFTBridgeControlHarness bridgeControl;

    function setUp() public {
        endpoint = new MockEndpoint();
        nftFactory = new NFTFactory();
        bridgeControl = new NFTBridgeControlHarness(address(endpoint), address(nftFactory), TEST_EID);
        bridgeControl.setOriginCaller(ORIGIN_SENDER.toAddress());
        vm.roll(100000000);
    }

    function _fastForwardThreeMonths() internal {
        vm.roll(block.number + 777660001);
    }


    function test_validateOrigin() public {
        Origin memory origin = Origin(TEST_EID, ORIGIN_SENDER, 0);
        bridgeControl.validateOrigin(origin); // validate fn reverts on failure

        bytes32 BOGUS_SENDER = address(0x1234).toBytes32();
        vm.expectRevert();
        bridgeControl.validateOrigin(Origin(TEST_EID, BOGUS_SENDER, 1));

        uint32 BOGUS_EID = 2;
        vm.expectRevert();
        bridgeControl.validateOrigin(Origin(BOGUS_EID, ORIGIN_SENDER, 1));
    }

    function test_validateGuidProcessedExactlyOnce() public {
        bytes32 guid = bytes32(uint256(1));
        bridgeControl.validateGuid(guid);
        vm.expectRevert();
        bridgeControl.validateGuid(guid);
    }

    function test_payloadHandled()public {
        address collectionAddress = address(0x1001);
        bytes memory payload = abi.encode(collectionAddress);
        assertEq(bridgeControl.bridgingApproved(collectionAddress), false);
        address parsedAddress = bridgeControl.handlePayload(payload);
        assertEq(parsedAddress, collectionAddress);
        assertEq(bridgeControl.bridgingApproved(collectionAddress), true);
    }

    function test_adminCanSetBridgingApproved() public {
        address collectionAddress = address(0x1001);
        assertEq(bridgeControl.bridgingApproved(collectionAddress), false);
        bridgeControl.adminSetBridgingApproved(collectionAddress, true);
        assertEq(bridgeControl.bridgingApproved(collectionAddress), true);

        // disapprove
        bridgeControl.adminSetBridgingApproved(collectionAddress, false);
        assertEq(bridgeControl.bridgingApproved(collectionAddress), false);

        // only admin can set
        vm.expectRevert();
        vm.prank(ATTACKER);
        bridgeControl.adminSetBridgingApproved(collectionAddress, true);
    }

    function test_adminCanSetCanDeploy() public {
        address account = address(0x1001);
        assertEq(bridgeControl.canDeploy(account), false);
        bridgeControl.setCanDeploy(account, true);
        assertEq(bridgeControl.canDeploy(account), true);

        // disapprove
        bridgeControl.setCanDeploy(account, false);
        assertEq(bridgeControl.canDeploy(account), false);

        // only admin can set
        vm.expectRevert();
        vm.prank(ATTACKER);
        bridgeControl.setCanDeploy(account, true);
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

        // check didBridge is false
        assertEq(bridgeControl.didBridge(originalAddress), false);

        address newCollection = bridgeControl.deployERC721(originalAddress, originalOwner, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps, isEnumerable);
        assertEq(bridgeControl.bridgedAddressForOriginal(originalAddress), newCollection);
        assertEq(bridgeControl.originalOwnerForCollection(newCollection), originalOwner);

        // check didBridge is true
        assertEq(bridgeControl.didBridge(originalAddress), true);

        address recipient = address(0x1004);
        bridgeControl.mint721(newCollection, recipient, 1);
        assertEq(IERC721(newCollection).ownerOf(1), recipient);
    }

    function test_AdminCannotMintAfterAdminPeriod() public {
        address originalAddress = address(0x1001);
        address originalOwner = address(0x1002);
        string memory name = "Test Collection";
        string memory symbol = "TST";
        string memory baseURI = "https://test.com/";
        string memory extension = ".json";
        address royaltyRecipient = address(0x1003);
        uint256 royaltyBps = 1000;
        bool isEnumerable = false;

        // check didBridge is false
        assertEq(bridgeControl.didBridge(originalAddress), false);

        address newCollection = bridgeControl.deployERC721(originalAddress, originalOwner, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps, isEnumerable);
        assertEq(bridgeControl.bridgedAddressForOriginal(originalAddress), newCollection);
        assertEq(bridgeControl.originalOwnerForCollection(newCollection), originalOwner);

        // check didBridge is true
        assertEq(bridgeControl.didBridge(originalAddress), true);

        _fastForwardThreeMonths();
        address recipient = address(0x1004);
        vm.expectRevert();
        bridgeControl.mint721(newCollection, recipient, 1);
        //vm.expectRevert();
        //IERC721(newCollection).ownerOf(1);
    }

    function test_OriginalOwnerCanClaim() public {
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

        // attacker cannot claim
        vm.expectRevert();
        vm.prank(ATTACKER);
        bridgeControl.claimOwnership(newCollection);

        // original owner can claim
        vm.prank(originalOwner);
        bridgeControl.claimOwnership(newCollection);
    }

    function test_OwnerCanWithdraw() public {
        vm.deal(address(bridgeControl), 1 ether);
        assertEq(address(bridgeControl).balance, 1 ether);

        // attacker cannot withdraw
        vm.expectRevert();
        vm.prank(ATTACKER);
        bridgeControl.withdraw();

        // owner can withdraw
        bridgeControl.withdraw();
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
        bridgeControl.mint721(newCollection, recipient, 1);
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
        bridgeControl.mint1155(newCollection, recipient, 1, 1, "");
        assertEq(ERC1155(newCollection).balanceOf(recipient, 1), 1);
    }

    function test_canMint721ViaAirdrop() public {
        address originalAddress = address(0x1001);
        address originalOwner = address(0x1002);
        string memory name = "Test Collection";
        string memory symbol = "TST";
        string memory baseURI = "https://test.com/";
        string memory extension = ".json";
        address royaltyRecipient = address(0x1003);
        uint256 royaltyBps = 1000;
        bool isEnumerable = false;

        // check didBridge is false
        assertEq(bridgeControl.didBridge(originalAddress), false);

        address newCollection = bridgeControl.deployERC721(originalAddress, originalOwner, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps, isEnumerable);
        assertEq(bridgeControl.bridgedAddressForOriginal(originalAddress), newCollection);
        assertEq(bridgeControl.originalOwnerForCollection(newCollection), originalOwner);

        address recipient = address(0x1004);

        ERC721.AirdropUnit[] memory units = new ERC721.AirdropUnit[](1);
        uint256[] memory ids = new uint256[](1);
        ids[0] = 1;
        units[0] = ERC721.AirdropUnit(recipient, ids);

        bridgeControl.airdrop721(newCollection, units);
        assertEq(IERC721(newCollection).ownerOf(1), recipient);
    }


    function test_canMint1155ViaAirdrop() public {
        address originalAddress = address(0x1001);
        address originalOwner = address(0x1002);
        address royaltyRecipient = address(0x1003);
        uint256 royaltyBps = 1000;
        string memory uri = "https://test.com/";
        address newCollection = bridgeControl.deployERC1155(originalAddress, originalOwner, royaltyRecipient, royaltyBps, uri);
        assertEq(bridgeControl.bridgedAddressForOriginal(originalAddress), newCollection);
        assertEq(bridgeControl.originalOwnerForCollection(newCollection), originalOwner);

        address recipient = address(0x1004);

        ERC1155.AirdropUnit[] memory units = new ERC1155.AirdropUnit[](1);
        uint256[] memory ids = new uint256[](1);
        uint256[] memory amounts = new uint256[](1);
        bytes memory data = new bytes(1);
        ids[0] = 1;
        amounts[0] = 100;
        units[0] = ERC1155.AirdropUnit(recipient, ids, amounts, data);

        bridgeControl.airdrop1155(newCollection, units);
        assertEq(ERC1155(newCollection).balanceOf(recipient, 1), 100);
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

    // needed for testing the withdraw method
    fallback() external payable {
    }

}
