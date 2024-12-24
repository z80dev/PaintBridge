// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

import {ERC721} from "./ERC721.sol";
import {ERC721Enumerable} from "./ERC721Enumerable.sol";
import {ERC1155} from "./ERC1155.sol";

contract NFTFactory {

    function deployERC721(address originalAddress,
                          address originalOwner,
                          string memory name,
                          string memory symbol,
                          string memory baseURI,
                          string memory extension,
                          address royaltyRecipient,
                          uint256 royaltyBps) public returns (address)
    {
        ERC721 newCollection = new ERC721(originalAddress, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps);
        newCollection.setAdmin(msg.sender);
        newCollection.renounceRights();
        address newAddress = address(newCollection);
        return newAddress;
    }

    function deployERC721Enumerable(address originalAddress,
                                    address originalOwner,
                                    string memory name,
                                    string memory symbol,
                                    string memory baseURI,
                                    string memory extension,
                                    address royaltyRecipient,
                                    uint256 royaltyBps) public returns (address)
    {
        ERC721 newCollection = new ERC721Enumerable(originalAddress, name, symbol, baseURI, extension, royaltyRecipient, royaltyBps);
        newCollection.setAdmin(msg.sender);
        newCollection.renounceRights();
        address newAddress = address(newCollection);
        return newAddress;
    }

    function deployERC1155(address originalAddress,
                           address originalOwner,
                           address royaltyRecipient,
                           uint256 royaltyBps) public returns (address)
    {
        ERC1155 newCollection = new ERC1155(originalAddress, royaltyRecipient, royaltyBps);
        newCollection.setAdmin(msg.sender);
        newCollection.renounceRights();
        address newAddress = address(newCollection);
        return newAddress;
    }

}
