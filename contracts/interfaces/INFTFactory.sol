// SPDX-License-Identifier: MIT

pragma solidity >=0.8.7 <0.9.0;

interface INFTFactory {
    function deployERC721(
        address originalAddress,
        string memory name,
        string memory symbol,
        string memory baseURI,
        string memory extension,
        address royaltyRecipient,
        uint256 royaltyBps
    ) external returns (address);

    function deployERC721Enumerable(
        address originalAddress,
        string memory name,
        string memory symbol,
        string memory baseURI,
        string memory extension,
        address royaltyRecipient,
        uint256 royaltyBps
    ) external returns (address);

    function deployERC1155(address originalAddress, address royaltyRecipient, uint256 royaltyBps)
        external
        returns (address);
}
