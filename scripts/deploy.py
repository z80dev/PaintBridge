#!/usr/bin/env python3

from ape import project, accounts
import json


JSON_PATH = "addresses.json"


# function to write the address of the deployed contract to a json file
# if the file doesn't exist, create it
# if the file exists, update it
def write_to_json(address):
    try:
        with open(JSON_PATH, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    data["factory"] = address
    with open(JSON_PATH, "w") as f:
        json.dump(data, f)


def main():
    deployer = accounts.load("painter")
    deployer.set_autosign(True, " ")
    project.provider.set_balance(deployer.address, 100 * 10**18)
    factory = project.ERC721Factory.deploy(sender=deployer)
    print(f"Factory deployed at {factory.address}")
    write_to_json(factory.address)
