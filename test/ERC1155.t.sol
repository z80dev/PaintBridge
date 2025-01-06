// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import {Test, console} from "forge-std/Test.sol";
import {ERC1155} from "../contracts/ERC1155.sol";

contract ERC1155Test is Test {

    ERC1155 nft;
    address royaltyRecipient = address(0x5678);
    uint256 royaltyBps = 1000;
    address validRecipient = address(0x1234);

    function setUp() public {
        nft = new ERC1155(address(0x1234), royaltyRecipient, royaltyBps);
    }

    function test_MintingRights() public {
        // deployer can mint
        nft.mint(validRecipient, 1, 1, "");

        // non-deployer cannot mint
        address attacker = address(0x4321);
        vm.expectRevert();
        vm.prank(attacker);
        nft.mint(attacker, 2, 1, "");

        // deployer can grant minting rights
        nft.setCanMint(attacker);
        vm.prank(attacker);
        nft.mint(attacker, 2, 1, "");

        // minting fails after revoking minting rights
        vm.prank(attacker);
        nft.renounceMintingRights();
        vm.expectRevert();
        vm.prank(attacker);
        nft.mint(attacker, 3, 1, "");

        // only admin can close mint
        vm.expectRevert();
        vm.prank(attacker);
        nft.closeMinting();

        // no minting after minting is closed
        nft.closeMinting();
        vm.expectRevert();
        nft.mint(validRecipient, 4, 1, "");
    }

    // function test_CanAirdrop() public {
    //     uint256[] memory ids = new uint256[](3);
    //     ids[0] = 1;
    //     ids[1] = 2;
    //     ids[2] = 3;
    //     ERC721.AirdropUnit memory unit = ERC721.AirdropUnit({
    //         to: validRecipient,
    //         ids: ids
    //     });
    //     ERC721.AirdropUnit[] memory units = new ERC721.AirdropUnit[](1);
    //     units[0] = unit;

    //     // airdrop fails if not admin
    //     address attacker = address(0x4321);
    //     vm.expectRevert();
    //     vm.prank(attacker);
    //     nft.bulkAirdrop(units);

    //     // succesful airdrop
    //     nft.bulkAirdrop(units);
    //     assertEq(nft.ownerOf(1), validRecipient);

    //     // airdrop fails if tokenIds already minted
    //     vm.expectRevert();
    //     nft.bulkAirdrop(units);

    //     // airdrop fails if mint is closed
    //     nft.closeMinting();
    //     uint256[] memory ids2 = new uint256[](1);
    //     ids2[0] = 4;
    //     ERC721.AirdropUnit memory unit2 = ERC721.AirdropUnit({
    //         to: validRecipient,
    //         ids: ids2
    //     });
    //     ERC721.AirdropUnit[] memory units2 = new ERC721.AirdropUnit[](1);
    //     units2[0] = unit2;
    //     vm.expectRevert();
    //     nft.bulkAirdrop(units2);
    // }

    function test_AdminCanBatchSetTokenURIs() public {
        uint256[] memory ids = new uint256[](3);
        ids[0] = 1;
        ids[1] = 2;
        ids[2] = 3;
        uint256[] memory amounts = new uint256[](3);
        amounts[0] = 1;
        amounts[1] = 1;
        amounts[2] = 1;
        ERC1155.AirdropUnit memory unit = ERC1155.AirdropUnit({
            to: validRecipient,
            ids: ids,
            amounts: amounts
        });
        ERC1155.AirdropUnit[] memory units = new ERC1155.AirdropUnit[](1);
        units[0] = unit;
        nft.bulkAirdrop(units);

        string[] memory uris = new string[](3);
        uris[0] = "uri1";
        uris[1] = "uri2";
        uris[2] = "uri3";
        nft.batchSetTokenURIs(1, uris);
        assertEq(keccak256(bytes(nft.uri(1))), keccak256(bytes("uri1")));
        assertEq(keccak256(bytes(nft.uri(2))), keccak256(bytes("uri2")));
        assertEq(keccak256(bytes(nft.uri(3))), keccak256(bytes("uri3")));

        // only admin can batch set token URIs
        address attacker = address(0x4321);
        vm.expectRevert();
        vm.prank(attacker);
        nft.batchSetTokenURIs(1, uris);
    }

    function test_URI() public {
        // test tokenURI
        nft.mint(validRecipient, 2, 1, "");
        string[] memory uris = new string[](1);
        uris[0] = "uri2";
        nft.batchSetTokenURIs(2, uris);
        assertEq(keccak256(bytes(nft.uri(2))), keccak256(bytes("uri2")));
    }

    function testFail_tokenURITokenDoesNotExist() public {
        nft.uri(1);
    }

}
