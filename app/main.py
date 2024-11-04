#!/usr/bin/env python3

from flask import Flask, jsonify

from .nft import airdrop_holders, deploy_1155, get_bridged_address, get_collection_data, deploy_721, get_holders_via_api, get_nft_royalty_info, get_onchain_royalty_info, get_token_uris, set_token_uris
from .config import get_config

app = Flask(__name__)
app.config.from_object(get_config())


@app.route('/api/bridge/<param>', methods=['GET'])
def bridge(param):
    if bridged_addr := get_bridged_address(param):
        return jsonify({"error": "Already bridged",
                         "original_address": param,
                         "bridged_address": bridged_addr})
    original_address = param
    holders = get_holders_via_api(original_address)
    airdrop_units = list(holders.values())
    is721 = airdrop_units[0].is721
    base_uri = "" # will use below for checking if we need to set uris manually
    try:
        royalty_data = get_nft_royalty_info(original_address)
    except:
        royalty_data = get_onchain_royalty_info(original_address)
    recipient = royalty_data["recipient"]
    fee = royalty_data["fee"]

    if is721:
        name, symbol, base_uri, _, extension = get_collection_data(original_address)
        deployment_tx = deploy_721(original_address, name, symbol, base_uri, extension, recipient, fee)
    else:
        deployment_tx = deploy_1155(original_address, recipient, fee)

    bridged_address = get_bridged_address(original_address)
    if not bridged_address:
        return jsonify({"error": "Failed to deploy contract to target chain", "original_address": original_address})

    airdrop_txs = airdrop_holders(bridged_address, airdrop_units)
    airdrop_tx_hashes = [tx.txn_hash for tx in airdrop_txs]

    response = {
        "original_address": original_address,
        "bridged_address": bridged_address,
        "deployment_tx": deployment_tx.txn_hash,
        "airdrop_txs": airdrop_tx_hashes
    }

    if not is721 or base_uri == "":
        uris = get_token_uris(original_address, is721=is721)
        uri_txs = set_token_uris(bridged_address, uris)
        response["uri_txs"] = [tx.txn_hash for tx in uri_txs]
    return jsonify(response)

@app.route('/api/getBridgedAddress/<param>', methods=['GET'])
def getBridgedAddress(param):
    bridged_address = get_bridged_address(param)
    return jsonify({"bridged_address": bridged_address})
