// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import {Test, console} from "forge-std/Test.sol";
import {ERC721} from "../contracts/ERC721.sol";

contract ERC721Test is Test {
    ERC721 nft;
    address royaltyRecipient = address(0x5678);
    uint256 royaltyBps = 1000;

    function setUp() public {
        nft = new ERC721(address(0x1234), "name", "symbol", "baseURI", "extension", royaltyRecipient, royaltyBps);
    }

    function test_GettersWork() public {
        assertEq(nft.name(), "name");
        assertEq(nft.symbol(), "symbol");
    }

    function test_MintingRights() public {
        // deployer can mint
        uint256[] memory ids = new uint256[](1);
        ids[0] = 1;
        ERC721.AirdropUnit[] memory units = new ERC721.AirdropUnit[](1);
        units[0] = ERC721.AirdropUnit({to: address(this), ids: ids});
        nft.bulkAirdrop(units);

        // non-deployer cannot mint
        address attacker = address(0x4321);
        uint256[] memory attackerIds = new uint256[](1);
        attackerIds[0] = 2;
        ERC721.AirdropUnit[] memory attackerUnits = new ERC721.AirdropUnit[](1);
        attackerUnits[0] = ERC721.AirdropUnit({to: attacker, ids: attackerIds});
        vm.expectRevert();
        vm.prank(attacker);
        nft.bulkAirdrop(attackerUnits);

        // deployer can grant minting rights
        nft.setCanMint(attacker, true);
        vm.prank(attacker);
        nft.bulkAirdrop(attackerUnits);

        // minting fails after revoking minting rights
        vm.prank(attacker);
        nft.renounceMintingRights();
        vm.expectRevert();
        vm.prank(attacker);
        nft.bulkAirdrop(attackerUnits);

        // only admin can close mint
        vm.expectRevert();
        vm.prank(attacker);
        nft.closeMinting();

        // no minting after minting is closed
        nft.closeMinting();
        vm.expectRevert();
        uint256[] memory finalIds = new uint256[](1);
        finalIds[0] = 4;
        ERC721.AirdropUnit[] memory finalUnits = new ERC721.AirdropUnit[](1);
        finalUnits[0] = ERC721.AirdropUnit({to: address(this), ids: finalIds});
        nft.bulkAirdrop(finalUnits);
    }

    function test_CanAirdrop() public {
        uint256[] memory ids = new uint256[](3);
        ids[0] = 1;
        ids[1] = 2;
        ids[2] = 3;
        ERC721.AirdropUnit memory unit = ERC721.AirdropUnit({to: address(this), ids: ids});
        ERC721.AirdropUnit[] memory units = new ERC721.AirdropUnit[](1);
        units[0] = unit;

        // airdrop fails if not admin
        address attacker = address(0x4321);
        vm.expectRevert();
        vm.prank(attacker);
        nft.bulkAirdrop(units);

        // succesful airdrop
        nft.bulkAirdrop(units);
        assertEq(nft.ownerOf(1), address(this));

        // airdrop succeeds and re-mints if tokenIds already minted
        nft.bulkAirdrop(units);

        // airdrop fails if mint is closed
        nft.closeMinting();
        uint256[] memory ids2 = new uint256[](1);
        ids2[0] = 4;
        ERC721.AirdropUnit memory unit2 = ERC721.AirdropUnit({to: address(this), ids: ids2});
        ERC721.AirdropUnit[] memory units2 = new ERC721.AirdropUnit[](1);
        units2[0] = unit2;
        vm.expectRevert();
        nft.bulkAirdrop(units2);
    }

    function test_AdminCanBatchSetTokenURIs() public {
        uint256[] memory ids = new uint256[](3);
        ids[0] = 1;
        ids[1] = 2;
        ids[2] = 3;
        ERC721.AirdropUnit memory unit = ERC721.AirdropUnit({to: address(this), ids: ids});
        ERC721.AirdropUnit[] memory units = new ERC721.AirdropUnit[](1);
        units[0] = unit;
        nft.bulkAirdrop(units);

        string[] memory uris = new string[](3);
        uris[0] = "uri1";
        uris[1] = "uri2";
        uris[2] = "uri3";
        nft.batchSetTokenURIs(1, uris);
        assertEq(keccak256(bytes(nft.tokenURI(1))), keccak256(bytes("uri1")));
        assertEq(keccak256(bytes(nft.tokenURI(2))), keccak256(bytes("uri2")));
        assertEq(keccak256(bytes(nft.tokenURI(3))), keccak256(bytes("uri3")));

        // only admin can batch set token URIs
        address attacker = address(0x4321);
        vm.expectRevert();
        vm.prank(attacker);
        nft.batchSetTokenURIs(1, uris);
    }

    function test_URI() public {
        // test baseURI from constructor
        uint256[] memory ids = new uint256[](1);
        ids[0] = 1;
        ERC721.AirdropUnit[] memory units = new ERC721.AirdropUnit[](1);
        units[0] = ERC721.AirdropUnit(address(this), ids);
        nft.bulkAirdrop(units);
        assertEq(keccak256(bytes(nft.tokenURI(1))), keccak256(bytes("baseURI1extension")));

        // set baseURI
        nft.setBaseURI("newBaseURI");
        assertEq(keccak256(bytes(nft.tokenURI(1))), keccak256(bytes("newBaseURI1extension")));

        // only admin can set baseURI
        address attacker = address(0x4321);
        vm.expectRevert();
        vm.prank(attacker);
        nft.setBaseURI("newBaseURI2");

        // test tokenURI
        ids[0] = 2;
        units[0] = ERC721.AirdropUnit(address(this), ids);
        nft.bulkAirdrop(units);
        string[] memory uris = new string[](1);
        uris[0] = "uri2";
        nft.batchSetTokenURIs(2, uris);
        assertEq(keccak256(bytes(nft.tokenURI(2))), keccak256(bytes("uri2")));
    }

    function testFail_tokenURITokenDoesNotExist() public {
        nft.tokenURI(1);
    }
}
