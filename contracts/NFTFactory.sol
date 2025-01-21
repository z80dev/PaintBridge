// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import {ERC721} from "./ERC721.sol";
import {ERC721Enumerable} from "./ERC721Enumerable.sol";
import {ERC1155} from "./ERC1155.sol";
import {Ownable} from "./Ownable.sol";

contract ERC721Factory {
    function deployERC721(
        address originalAddress,
        string memory name,
        string memory symbol,
        string memory baseURI,
        string memory extension,
        address royaltyRecipient,
        uint256 royaltyBps
    ) public returns (address) {
        ERC721 newCollection =
            new ERC721(originalAddress, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps);
        Ownable(newCollection).transferOwnership(msg.sender);
        return address(newCollection);
    }

    function deployERC721Enumerable(
        address originalAddress,
        string memory name,
        string memory symbol,
        string memory baseURI,
        string memory extension,
        address royaltyRecipient,
        uint256 royaltyBps
    ) public returns (address) {
        ERC721 newCollection =
            new ERC721Enumerable(originalAddress, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps);
        Ownable(newCollection).transferOwnership(msg.sender);
        return address(newCollection);
    }
}

contract ERC1155Factory {
    function deployERC1155(address originalAddress, address royaltyRecipient, uint256 royaltyBps)
        public
        returns (address)
    {
        ERC1155 newCollection = new ERC1155(originalAddress, royaltyRecipient, royaltyBps);
        Ownable(newCollection).transferOwnership(msg.sender);
        return address(newCollection);
    }
}

contract NFTFactory {
    ERC721Factory public immutable erc721Factory;
    ERC1155Factory public immutable erc1155Factory;

    constructor(address _erc721Factory, address _erc1155Factory) {
        erc721Factory = ERC721Factory(_erc721Factory);
        erc1155Factory = ERC1155Factory(_erc1155Factory);
    }

    function deployERC721(
        address originalAddress,
        string memory name,
        string memory symbol,
        string memory baseURI,
        string memory extension,
        address royaltyRecipient,
        uint256 royaltyBps
    ) public returns (address newContract) {
        newContract =
            erc721Factory.deployERC721(originalAddress, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps);
        Ownable(newContract).transferOwnership(msg.sender);
        return newContract;
    }

    function deployERC721Enumerable(
        address originalAddress,
        string memory name,
        string memory symbol,
        string memory baseURI,
        string memory extension,
        address royaltyRecipient,
        uint256 royaltyBps
    ) public returns (address newContract) {
        newContract = erc721Factory.deployERC721Enumerable(
            originalAddress, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps
        );
        Ownable(newContract).transferOwnership(msg.sender);
        return newContract;
    }

    function deployERC1155(address originalAddress, address royaltyRecipient, uint256 royaltyBps)
        public
        returns (address newContract)
    {
        newContract = erc1155Factory.deployERC1155(originalAddress, royaltyRecipient, royaltyBps);
        Ownable(newContract).transferOwnership(msg.sender);
        return newContract;
    }
}
