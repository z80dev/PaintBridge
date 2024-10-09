#!/usr/bin/env python3

from flask import Flask, jsonify

from .nft import airdrop_holders, get_bridged_address, get_collection_data, deploy_collection
from .config import get_config

app = Flask(__name__)
app.config.from_object(get_config())

ZERO_ADDR = "0x0000000000000000000000000000000000000000"

# TODO: switch to post but keeping GET for now for easier browser testing
@app.route('/api/bridge/<param>', methods=['GET'])
def bridge(param):
    if get_bridged_address(param) != ZERO_ADDR:
        return jsonify({"error": "Already bridged",
                         "original_address": param,
                         "bridged_address": get_bridged_address(param)})
    # get collection info
    name, symbol, base_uri, has_extension, extension = get_collection_data(param)
    deployment_tx = deploy_collection(param, name, symbol, base_uri, extension)
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
