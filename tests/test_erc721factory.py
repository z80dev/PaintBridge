#!/usr/bin/env python3

from ape.api.address import Address
import pytest

DUMMY_EID = 1

@pytest.fixture
def deployer(accounts):
    return accounts[0]

@pytest.fixture
def mock_endpoint(project, deployer):
    return project.MockEndpoint.deploy(sender=deployer)

@pytest.fixture
def factory(project, deployer):
    return project.NFTFactory.deploy(sender=deployer)

@pytest.fixture
def bridge_control(project, deployer, mock_endpoint, factory):
    return project.SCCNFTBridge.deploy(mock_endpoint, factory, DUMMY_EID, sender=deployer)


def test_factory_deploy(factory):
    assert factory is not None
    assert factory.address is not None

def test_deploy_collection_through_factory(bridge_control, deployer, project):
    original_address = Address(1001)
    original_owner = deployer
    bridge_control.deployERC721(
        original_address,
        original_owner,
        "MyNFT",
        "MNFT",
        "http://localhost:8081/",
        ".json",
        deployer,
        0,
        False,
        sender=deployer,
    ).return_value
    assert bridge_control.didBridge(original_address)
    new_nft_addr = bridge_control.bridgedAddressForOriginal(original_address)
    new_nft = project.ERC721.at(new_nft_addr)
    assert project.ERC721.at(new_nft_addr).name() == "MyNFT"
    assert project.ERC721.at(new_nft_addr).symbol() == "MNFT"
    new_nft.mint(deployer, 1, sender=deployer)
    assert project.ERC721.at(new_nft_addr).tokenURI(1) == "http://localhost:8081/1.json"


def test_royalties(bridge_control, deployer, project):
    original_address = Address(1001)
    original_owner = deployer
    bridge_control.deployERC721(
        original_address,
        original_owner,
        "MyNFT",
        "MNFT",
        "http://localhost:8081/",
        ".json",
        deployer,
        600,
        False,
        sender=deployer,
    ).return_value
    assert bridge_control.didBridge(original_address)
    new_nft_addr = bridge_control.bridgedAddressForOriginal(original_address)
    new_nft = project.ERC721.at(new_nft_addr)
    ONE_ETH = 10**18
    royalty_info = new_nft.royaltyInfo(1, ONE_ETH)
    assert royalty_info[1] == 60000000000000000
    assert project.ERC721.at(new_nft_addr).name() == "MyNFT"
    assert project.ERC721.at(new_nft_addr).symbol() == "MNFT"
    new_nft.mint(deployer, 1, sender=deployer)
    assert project.ERC721.at(new_nft_addr).tokenURI(1) == "http://localhost:8081/1.json"


def test_deploy_enumerable_collection_through_factory(bridge_control, deployer, project):
    original_address = Address(1001)
    original_owner = deployer
    bridge_control.deployERC721(
        original_address,
        original_owner,
        "MyNFT",
        "MNFT",
        "http://localhost:8081/",
        ".json",
        deployer,
        0,
        True,
        sender=deployer,
    ).return_value
    assert bridge_control.didBridge(original_address)
    new_nft_addr = bridge_control.bridgedAddressForOriginal(original_address)
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
