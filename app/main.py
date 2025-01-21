from time import time
from flask import Flask, jsonify
from .config import env_vars
from .nft_bridge import NFTBridge
from .utils import has_too_many_nfts, has_too_many_owners, last_sale_within_six_months

app = Flask(__name__)

nft_bridge = NFTBridge(
    env_vars.DEPLOYER_NAME,
    env_vars.DEPLOYER_PASSWORD,
    env_vars.SOURCE_ENDPOINT_ADDRESS,
    env_vars.TARGET_ENDPOINT_ADDRESS,
    int(env_vars.EXPECTED_EID),
    env_vars.FACTORY_ADDRESS,
    env_vars.BRIDGE_CONTROL_ADDRESS,
    env_vars.AUTHORIZER_ADDRESS,
    env_vars.FLASK_ENV,
    skip_authorizer=True
)

@app.route("/api/bridge/<param>", methods=["GET"])
def bridge(param):
    if bridged_addr := nft_bridge.get_bridged_address(param):
        return jsonify({
            "error": "Already bridged",
            "original_address": param,
            "bridged_address": bridged_addr,
        })

    original_address = param
    holders = nft_bridge.get_holders_via_api(original_address)
    airdrop_units = list(holders.values())
    is721 = airdrop_units[0].is721
    base_uri = ""

    try:
        royalty_data = nft_bridge.get_nft_royalty_info(original_address)
    except Exception:
        royalty_data = nft_bridge.get_onchain_royalty_info(original_address)

    recipient = royalty_data["recipient"]
    fee = royalty_data["fee"]

    collection_data = nft_bridge.get_collection_data_api(original_address)
    # if not collection_data.get("verified"):
    #     return jsonify({
    #         "error": "Collection not verified",
    #         "original_address": original_address,
    #     })

    if has_too_many_nfts(collection_data):
        return jsonify({
            "error": "Collection has too many NFTs",
            "original_address": original_address,
            "total_nfts": collection_data.get("stats", {}).get("totalNFTs")
        })

    if has_too_many_owners(collection_data):
        return jsonify({
            "error": "Collection has too many owners",
            "original_address": original_address,
            "num_owners": collection_data.get("stats", {}).get("numOwners")
        })

    # if not last_sale_within_six_months(collection_data):
    #     return jsonify({
    #         "error": "Collection has not been sold in 6 months",
    #         "original_address": original_address,
    #     })

    original_owner = nft_bridge.get_collection_owner(original_address)
    if is721:
        name, symbol, base_uri, _, extension = nft_bridge.get_collection_data(original_address)
        deployment_tx = nft_bridge.deploy_721(
            original_address, original_owner, name, symbol, base_uri, extension, recipient, fee
        )
    else:
        deployment_tx = nft_bridge.deploy_1155(original_address, original_owner, recipient, fee)

    bridged_address = nft_bridge.get_bridged_address(original_address)
    if not bridged_address:
        return jsonify({
            "error": "Failed to deploy contract to target chain",
            "original_address": original_address,
        })

    airdrop_txs = nft_bridge.airdrop_holders(bridged_address, airdrop_units)
    airdrop_tx_hashes = [tx.txn_hash for tx in airdrop_txs]

    response = {
        "original_address": original_address,
        "bridged_address": bridged_address,
        "deployment_tx": deployment_tx.txn_hash,
        "airdrop_txs": airdrop_tx_hashes,
    }

    if not is721 or base_uri == "":
        uris = nft_bridge.get_token_uris(original_address, is721=is721)
        uri_txs = nft_bridge.set_token_uris(bridged_address, uris)
        response["uri_txs"] = [tx.txn_hash for tx in uri_txs]
    return jsonify(response)

@app.route("/api/getBridgedAddress/<param>", methods=["GET"])
def getBridgedAddress(param):
    bridged_address = nft_bridge.get_bridged_address(param)
    return jsonify({"bridged_address": bridged_address})
