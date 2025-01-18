#!/usr/bin/env python3

from ape import project, accounts

def main():
deployer = accounts.load("paintbot")
deployer.set_autosign(True, " ")
factory = project.NFTFactory.deploy(sender=deployer)
print(f"Factory deployed at {factory.address}")

tx = factory.deployERC721(
    "0x0000000000000000000000000000000000000000",
    "NFT Collection",
    "NFT",
    "ipfs://baseuri/",
    ".json",
    deployer.address,
    500, # 5% royalty
    sender=deployer
)
collection_address = tx.return_value
print(f"ERC721 deployed at {collection_address}")

# mint some tokens
collection = project.ERC721.at(collection_address)
tx = collection.bulkAirdrop([(deployer.address, [1, 2, 3])], sender=deployer)
print("Tokens minted")
print(f"https://ftmscan.org/tx/{tx.txid}")
