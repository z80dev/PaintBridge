#!/usr/bin/env python3

from flask import Flask, jsonify

from .nft import airdrop_holders, airdrop_holders_improved, deploy_1155, get_bridged_address, get_collection_data, deploy_721, get_holders_via_api_improved, get_token_uris, set_token_uris
from .config import get_config

app = Flask(__name__)
app.config.from_object(get_config())

ZERO_ADDR = "0x0000000000000000000000000000000000000000"

@app.route('/api/getURIs/<param>', methods=['GET'])
def getURIs(param):
    uris = get_token_uris(param)
    count = len(uris)
    return jsonify({"count": count, "uris": uris})

@app.route('/api/bridge2/<param>', methods=['GET'])
def bridge2(param):
    if get_bridged_address(param) != ZERO_ADDR:
        return jsonify({"error": "Already bridged",
                         "original_address": param,
                         "bridged_address": get_bridged_address(param)})
    response = {}
    original_address = param
    holders = get_holders_via_api_improved(original_address)
    airdrop_units = list(holders.values())
    is721 = airdrop_units[0].is721
    if is721:
        name, symbol, base_uri, _, extension = get_collection_data(original_address)
        deployment_tx = deploy_721(original_address, name, symbol, base_uri, extension)
    else:
        deployment_tx = deploy_1155(original_address)

    bridged_address = get_bridged_address(original_address)
    airdrop_txs = airdrop_holders_improved(bridged_address, airdrop_units)
    air_drop_tx_hashes = [tx.txn_hash for tx in airdrop_txs]

    response["bridged_address"] = bridged_address
    response["original_address"] = original_address
    response["deployment_tx"] = deployment_tx.txn_hash
    response["airdrop_txs"] = air_drop_tx_hashes

    if not is721:
        uris = get_token_uris(original_address)
        uri_txs = set_token_uris(bridged_address, uris)
        response["uri_txs"] = [tx.txn_hash for tx in uri_txs]

    return jsonify(response)


# TODO: switch to post but keeping GET for now for easier browser testing
@app.route('/api/bridge/<param>', methods=['GET'])
def bridge(param):
    if get_bridged_address(param) != ZERO_ADDR:
        return jsonify({"error": "Already bridged",
                         "original_address": param,
                         "bridged_address": get_bridged_address(param)})
    # get collection info
    name, symbol, base_uri, has_extension, extension = get_collection_data(param)
    deployment_tx = deploy_721(param, name, symbol, base_uri, extension)
    new_address = get_bridged_address(param)
    airdrop_txs = airdrop_holders(param)
    airdrop_tx_hashes = [tx.txn_hash for tx in airdrop_txs]
    return jsonify({"bridged_address": new_address,
                    "original_address": param,
                    "deployment_tx": deployment_tx.txn_hash,
                    "airdrop_txs": airdrop_tx_hashes})

@app.route('/api/getBridgedAddress/<param>', methods=['GET'])
def getBridgedAddress(param):
    bridged_address = get_bridged_address(param)
    return jsonify({"bridged_address": bridged_address})
