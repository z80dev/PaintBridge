#!/usr/bin/env python3

from ape.api.address import Address
import pytest

@pytest.fixture
def deployer(accounts):
    return accounts[0]

@pytest.fixture
def factory(project, deployer):
    return project.ERC721Factory.deploy(sender=deployer)

def test_factory_deploy(factory):
    assert factory is not None
    assert factory.address is not None

def test_deploy_collection_through_factory(factory, deployer, project):
    original_address = Address(1001)
    factory.deployERC721(original_address, "MyNFT", "MNFT", "http://localhost:8081/", ".json", sender=deployer).return_value
    assert factory.didBridge(original_address)
    new_nft_addr = factory.bridgedAddressForOriginal(original_address)
    new_nft = project.ERC721.at(new_nft_addr)
    assert project.ERC721.at(new_nft_addr).name() == "MyNFT"
    assert project.ERC721.at(new_nft_addr).symbol() == "MNFT"
    new_nft.mint(deployer, 1, sender=deployer)
    assert project.ERC721.at(new_nft_addr).tokenURI(1) == "http://localhost:8081/1.json"
