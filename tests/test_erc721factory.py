#!/usr/bin/env python3

from ape.api.address import Address
import pytest


@pytest.fixture
def deployer(accounts):
    return accounts[0]


@pytest.fixture
def factory(project, deployer):
    return project.NFTFactory.deploy(sender=deployer)


def test_factory_deploy(factory):
    assert factory is not None
    assert factory.address is not None


def test_deploy_collection_through_factory(factory, deployer, project):
    original_address = Address(1001)
    factory.deployERC721(
        original_address,
        "MyNFT",
        "MNFT",
        "http://localhost:8081/",
        ".json",
        deployer,
        0,
        sender=deployer,
    ).return_value
    assert factory.didBridge(original_address)
    new_nft_addr = factory.bridgedAddressForOriginal(original_address)
    new_nft = project.ERC721.at(new_nft_addr)
    assert project.ERC721.at(new_nft_addr).name() == "MyNFT"
    assert project.ERC721.at(new_nft_addr).symbol() == "MNFT"
    new_nft.mint(deployer, 1, sender=deployer)
    assert project.ERC721.at(new_nft_addr).tokenURI(1) == "http://localhost:8081/1.json"


def bps_to_scaled_denominator(bps, scaling_factor):
    """
    Convert a fee in basis points to a scaled denominator.

    Args:
        bps (int): Fee in basis points (e.g., 500 for 5%)
        scaling_factor (int): Scaling factor for precision (e.g., 10**10)

    Returns:
        int: Scaled denominator to use in smart contract calculations
    """
    return (scaling_factor * 10000) // bps


def test_royalties(factory, deployer, project):
    original_address = Address(1001)
    factory.deployERC721(
        original_address,
        "MyNFT",
        "MNFT",
        "http://localhost:8081/",
        ".json",
        deployer,
        600,
        sender=deployer,
    ).return_value
    assert factory.didBridge(original_address)
    new_nft_addr = factory.bridgedAddressForOriginal(original_address)
    new_nft = project.ERC721.at(new_nft_addr)
    ONE_ETH = 10**18
    royalty_info = new_nft.royaltyInfo(1, ONE_ETH)
    assert royalty_info[1] == 60000000000000000
    assert project.ERC721.at(new_nft_addr).name() == "MyNFT"
    assert project.ERC721.at(new_nft_addr).symbol() == "MNFT"
    new_nft.mint(deployer, 1, sender=deployer)
    assert project.ERC721.at(new_nft_addr).tokenURI(1) == "http://localhost:8081/1.json"


def test_deploy_enumerable_collection_through_factory(factory, deployer, project):
    original_address = Address(1001)
    factory.deployERC721Enumerable(
        original_address,
        "MyNFT",
        "MNFT",
        "http://localhost:8081/",
        ".json",
        deployer,
        0,
        sender=deployer,
    ).return_value
    assert factory.didBridge(original_address)
    new_nft_addr = factory.bridgedAddressForOriginal(original_address)
    new_nft = project.ERC721.at(new_nft_addr)
    assert project.ERC721.at(new_nft_addr).name() == "MyNFT"
    assert project.ERC721.at(new_nft_addr).symbol() == "MNFT"
    new_nft.mint(deployer, 1, sender=deployer)
    assert project.ERC721.at(new_nft_addr).tokenURI(1) == "http://localhost:8081/1.json"
    assert project.ERC721Enumerable.at(new_nft_addr).totalSupply() == 1
    assert project.ERC721Enumerable.at(new_nft_addr).tokenByIndex(0) == 1
    assert (
        project.ERC721Enumerable.at(new_nft_addr).tokenOfOwnerByIndex(deployer, 0) == 1
    )
