import os
import time
import dotenv
dotenv.load_dotenv()
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from ape.logging import logger as ape_logger, LogLevel
from .config import env_vars

from .nft_bridge import NFTBridge

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

ape_logger.set_level(LogLevel.ERROR)

nft_bridge = NFTBridge(
    env_vars.DEPLOYER_NAME,
    env_vars.DEPLOYER_PASSWORD,
    env_vars.SOURCE_ENDPOINT_ADDRESS,
    env_vars.TARGET_ENDPOINT_ADDRESS,
    int(env_vars.EXPECTED_EID),
    env_vars.FACTORY_ADDRESS,
    env_vars.BRIDGE_CONTROL_ADDRESS,
    env_vars.AUTHORIZER_ADDRESS,
    env_vars.FLASK_ENV
)

def tx_hash_to_link(tx_hash: str) -> str:
    if env_vars.FLASK_ENV == 'prod':
        return f"https://sonicscan.org/tx/{tx_hash}"
    return f"https://testnet.soniclabs.com/tx/{tx_hash}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello! I can bridge NFTs for you.")

async def bridge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide an address to bridge.")
        return
    param = ''.join(context.args)
    if bridged_addr := nft_bridge.get_bridged_address(param):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Already bridged: {bridged_addr}")
        return
    collection_data = nft_bridge.get_collection_data_api(param)
    if not collection_data.get("verified"):
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Collection not verified: {param}")
        return
    if stats := collection_data.get("stats"):
        total_nfts = int(stats.get("totalNFTs"))
        num_owners = int(stats.get("numOwners"))
        if total_nfts > 11000:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Collection has too many NFTs: {param} {total_nfts} tokenIds")
            return
        if num_owners > 11000:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Collection has too many owners: {param} {num_owners} owners")
            return
        # fail if the collection has not been sold in 6 months
        last_sale = int(stats.get("timestampLastSale"))
        current_time = int(time.time())
        print(f"Last sale: {last_sale}")
        print(f"Current time: {current_time}")
        print(f"Diff: {current_time - last_sale}")
        six_months = 6 * 30 * 24 * 60 * 60
        print(f"Six months: {six_months}")
        if current_time - last_sale > six_months:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Collection has not been sold in 6 months: {param}")
            return
    msg = f"Bridging collection {param}\n"
    original_address = param
    holders = nft_bridge.get_holders_via_api(original_address)
    airdrop_units = list(holders.values())
    num_holders = len(holders.keys())
    is721 = airdrop_units[0].is721
    if is721:
        msg += f"Collection is 721\n"
    else:
        msg += f"Collection is 1155\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    base_uri = ""  # will use below for checking if we need to set uris manually
    try:
        royalty_data = nft_bridge.get_nft_royalty_info(original_address)
        assert royalty_data is not None
    except Exception:
        royalty_data = nft_bridge.get_onchain_royalty_info(original_address)

    recipient = royalty_data["recipient"]
    fee = royalty_data["fee"]

    msg = f"*Royalty Info*\nRecipient: {recipient}\nFee: {fee}\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

    original_owner = nft_bridge.get_collection_owner(original_address)
    if is721:
        name, symbol, base_uri, _, extension = nft_bridge.get_collection_data(original_address)
        msg = f"*Collection Info*\nName: {name}\nSymbol: {symbol}\nBase URI: {base_uri}\nExtension: {extension}\nOwner: {original_owner}\n"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
        msg = f"Deploying 721 contract\n"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
        deployment_tx = nft_bridge.deploy_721(
            original_address, original_owner, name, symbol, base_uri, extension, recipient, fee
        )
        msg = f"Deployment tx: {tx_hash_to_link(deployment_tx.txn_hash)}\n"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    else:
        deployment_tx = nft_bridge.deploy_1155(original_address, original_owner, recipient, fee)

    bridged_address = nft_bridge.get_bridged_address(original_address)

    if not bridged_address:
        response_msg = f"Failed to deploy contract to target chain: {original_address}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response_msg)
        return
    else:
        response_msg = f"Original address: {original_address}\nBridged address: {bridged_address}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response_msg)

        msg = f"Airdropping tokens to {num_holders} holders\n"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
        airdrop_txs = nft_bridge.airdrop_holders(bridged_address, airdrop_units)
        airdrop_tx_links = [tx_hash_to_link(tx.txn_hash) for tx in airdrop_txs]
        response_msg = f"\nAirdrop txs:\n{'\n'.join(airdrop_tx_links)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response_msg)

        if not is721 or base_uri == "":
            uris = nft_bridge.get_token_uris(original_address, is721=is721)
            uri_txs = nft_bridge.set_token_uris(bridged_address, uris)
            uri_tx_links = [tx_hash_to_link(tx.txn_hash) for tx in uri_txs]
            response_msg = f"URI txs: {'\n'.join(uri_tx_links)}"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response_msg)

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide an address to approve.")
        return

    address = ''.join(context.args)
    try:
        tx = nft_bridge.admin_set_bridging_approved(address, True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Successfully approved {address}\nTx: {tx_hash_to_link(tx.txn_hash)}"
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Failed to approve {address}: {str(e)}"
        )

def main():
    if env_vars.TG_BOT_TOKEN is None:
        raise ValueError("Please set the TG_BOT_TOKEN environment variable")
    application = ApplicationBuilder().token(env_vars.TG_BOT_TOKEN).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    bridge_handler = CommandHandler('bridge', bridge)
    application.add_handler(bridge_handler)

    approve_handler = CommandHandler('approve', approve)  # Add this line
    application.add_handler(approve_handler)  # And this line

    application.run_polling()

if __name__ == '__main__':
    main()
