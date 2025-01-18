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

# Configure logging with more detailed format
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Set up file handler
file_handler = logging.FileHandler('nft_bridge_bot.log')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

ape_logger.set_level(LogLevel.ERROR)

logger.info("Initializing NFT Bridge...")
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
logger.info("NFT Bridge initialized successfully")

def tx_hash_to_link(tx_hash: str) -> str:
    env = env_vars.FLASK_ENV
    logger.debug(f"Generating transaction link for hash {tx_hash} in {env} environment")
    if env == 'prod':
        return f"https://sonicscan.org/tx/{tx_hash}"
    return f"https://testnet.soniclabs.com/tx/{tx_hash}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Start command received from user {update.effective_user.id}")
    msg_str = """Hello! I can bridge NFTs for you. Collection requirements:
- Must be verified
- Less than 11,000 total NFTs
- Less than 11,000 owners
- Must have had a sale in the last 6 months
- Must have been approved for bridging (by collection owner or admin)
Use /approve <address> to approve a collection for bridging
Use /bridge <address> to bridge a collection"""
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg_str)
    logger.debug("Start message sent successfully")

def has_too_many_nfts(collection_data: dict) -> bool:
    logger.debug(f"Checking NFT count for collection: {collection_data.get('stats', {}).get('totalNFTs')}")
    if stats := collection_data.get("stats"):
        total_nfts = int(stats.get("totalNFTs"))
        return total_nfts > 11000
    return False

def has_too_many_owners(collection_data: dict) -> bool:
    logger.debug(f"Checking owner count for collection: {collection_data.get('stats', {}).get('numOwners')}")
    if stats := collection_data.get("stats"):
        num_owners = int(stats.get("numOwners"))
        return num_owners > 11000
    return False

def last_sale_within_six_months(collection_data: dict) -> bool:
    logger.debug(f"Checking last sale timestamp: {collection_data.get('stats', {}).get('timestampLastSale')}")
    if stats := collection_data.get("stats"):
        last_sale = int(stats.get("timestampLastSale"))
        current_time = int(time.time())
        six_months = 6 * 30 * 24 * 60 * 60
        return current_time - last_sale <= six_months
    return False

async def validate_collection(update, context, addr, collection_data):
    logger.info(f"Validating collection {addr}")

    if not collection_data.get("verified"):
        logger.warning(f"Collection {addr} is not verified")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Collection not verified: {addr}")
        return False

    if has_too_many_nfts(collection_data):
        logger.warning(f"Collection {addr} has too many NFTs")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Collection has too many NFTs: {addr}")
        return False

    if has_too_many_owners(collection_data):
        logger.warning(f"Collection {addr} has too many owners")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Collection has too many owners: {addr}")
        return False

    if not last_sale_within_six_months(collection_data):
        logger.warning(f"Collection {addr} has no recent sales")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Collection has not been sold in 6 months: {addr}")
        return False

    logger.info(f"Collection {addr} passed all validation checks")
    return True

async def get_royalty_info(addr):
    logger.info(f"Fetching royalty info for {addr}")
    try:
        royalty_data = nft_bridge.get_nft_royalty_info(addr)
        if royalty_data is None:
            logger.warning(f"No royalty data found for {addr}, falling back to on-chain data")
            raise Exception("No royalty data found")
        logger.debug(f"Royalty data retrieved: {royalty_data}")
    except Exception as e:
        logger.info(f"Getting on-chain royalty info for {addr} due to: {str(e)}")
        royalty_data = nft_bridge.get_onchain_royalty_info(addr)
    return royalty_data

async def send_royalty_info(update, context, royalty_data):
    logger.debug(f"Sending royalty info: {royalty_data}")
    msg = f"*Royalty Info*\nRecipient: {royalty_data['recipient']}\nFee: {royalty_data['fee']}\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

async def handle_deployment(update, context, addr, is721, original_owner, royalty_data):
    logger.info(f"Handling deployment for {addr} (is721: {is721})")
    if is721:
        name, symbol, base_uri, _, extension = nft_bridge.get_collection_data(addr)
        logger.debug(f"ERC721 collection data: name={name}, symbol={symbol}, base_uri={base_uri}")

        msg = f"*Collection Info*\nName: {name}\nSymbol: {symbol}\nBase URI: {base_uri}\n" \
              f"Extension: {extension}\nOwner: {original_owner}\n"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

        logger.info("Deploying ERC721 contract")
        deployment_tx = nft_bridge.deploy_721(
            addr, original_owner, name, symbol, base_uri, extension,
            royalty_data["recipient"], royalty_data["fee"]
        )
        logger.info(f"ERC721 deployment transaction: {deployment_tx.txn_hash}")
        return deployment_tx, base_uri
    else:
        logger.info("Deploying ERC1155 contract")
        deployment_tx = nft_bridge.deploy_1155(
            addr, original_owner, royalty_data["recipient"], royalty_data["fee"]
        )
        logger.info(f"ERC1155 deployment transaction: {deployment_tx.txn_hash}")
        return deployment_tx, ""

async def handle_airdrop(update, context, bridged_address, airdrop_units):
    num_holders = len(airdrop_units)
    logger.info(f"Starting airdrop to {num_holders} holders for {bridged_address}")
    msg = f"Airdropping tokens to {num_holders} holders\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
    airdrop_txs = nft_bridge.airdrop_holders(bridged_address, airdrop_units)
    logger.info(f"Completed airdrop with {len(airdrop_txs)} transactions")
    return airdrop_txs

async def handle_uris(update, context, addr, bridged_address, is721, base_uri):
    logger.info(f"Handling URIs for {addr} (is721: {is721}, base_uri: {base_uri})")
    if not is721 or base_uri == "":
        logger.debug("Fetching token URIs")
        uris = nft_bridge.get_token_uris(addr, is721=is721)
        logger.debug(f"Setting {len(uris)} URIs")
        uri_txs = nft_bridge.set_token_uris(bridged_address, uris)
        uri_tx_links = [tx_hash_to_link(tx.txn_hash) for tx in uri_txs]
        response_msg = f"URI txs: {'\n'.join(uri_tx_links)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response_msg)
        logger.info(f"Set {len(uri_txs)} URIs successfully")

async def send_tx_status(update, context, tx, message):
    logger.debug(f"Sending transaction status: {message} - {tx.txn_hash}")
    msg = f"{message}: {tx_hash_to_link(tx.txn_hash)}\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

async def bridge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Bridge command received from user {update.effective_user.id}")
    assert update.effective_chat is not None

    if not context.args:
        logger.warning("No address provided for bridge command")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Please provide an address to bridge.")
        return

    addr = context.args[0]
    logger.info(f"Starting bridge process for address: {addr}")

    if bridged_addr := nft_bridge.get_bridged_address(addr):
        logger.info(f"Collection {addr} already bridged to {bridged_addr}")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                    text=f"Already bridged to {bridged_addr}. Use /remint {addr} to remint tokens to current holders.")
        return

    collection_data = nft_bridge.get_collection_data_api(addr)
    if not await validate_collection(update, context, addr, collection_data):
        logger.warning(f"Collection validation failed for {addr}")
        return

    logger.info(f"Starting bridging process for collection {addr}")
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Bridging collection {addr}\n")

    holders = nft_bridge.get_holders_via_api(addr)
    airdrop_units = list(holders.values())
    is721 = airdrop_units[0].is721
    logger.info(f"Collection type: {'ERC721' if is721 else 'ERC1155'}, holders: {len(holders)}")

    royalty_data = await get_royalty_info(addr)
    await send_royalty_info(update, context, royalty_data)

    original_owner = nft_bridge.get_collection_owner(addr)
    logger.info(f"Original collection owner: {original_owner}")

    deployment_tx, base_uri = await handle_deployment(update, context, addr, is721,
                                                    original_owner, royalty_data)
    await send_tx_status(update, context, deployment_tx, "Deployment tx")

    bridged_address = nft_bridge.get_bridged_address(addr)
    if not bridged_address:
        logger.error(f"Failed to deploy contract for {addr}")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Failed to deploy contract to target chain: {addr}")
        return

    logger.info(f"Successfully deployed contract: {bridged_address}")
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Original address: {addr}\nBridged address: {bridged_address}")

    airdrop_txs = await handle_airdrop(update, context, bridged_address, airdrop_units)
    airdrop_tx_links = [tx_hash_to_link(tx.txn_hash) for tx in airdrop_txs]
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"\nAirdrop txs:\n{'\n'.join(airdrop_tx_links)}")

    await handle_uris(update, context, addr, bridged_address, is721, base_uri)
    logger.info(f"Bridge process completed successfully for {addr}")

async def remint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Remint command received from user {update.effective_user.id}")
    assert update.effective_chat is not None

    if not context.args:
        logger.warning("No address provided for remint command")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Please provide an address to remint.")
        return

    addr = context.args[0]
    logger.info(f"Starting remint process for {addr}")

    bridged_addr = nft_bridge.get_bridged_address(addr)
    if not bridged_addr:
        logger.warning(f"Collection {addr} not yet bridged")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Collection not yet bridged. Use /bridge {addr} first.")
        return

    collection_data = nft_bridge.get_collection_data_api(addr)
    if not await validate_collection(update, context, addr, collection_data):
        logger.warning(f"Collection validation failed for remint of {addr}")
        return

    holders = nft_bridge.get_holders_via_api(addr)
    airdrop_units = list(holders.values())
    is721 = airdrop_units[0].is721
    logger.info(f"Reminting for {len(holders)} holders")

    airdrop_txs = await handle_airdrop(update, context, bridged_addr, airdrop_units)
    airdrop_tx_links = [tx_hash_to_link(tx.txn_hash) for tx in airdrop_txs]
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Remint txs:\n{'\n'.join(airdrop_tx_links)}")

    await handle_uris(update, context, addr, bridged_addr, is721, "")
    logger.info(f"Remint process completed successfully for {addr}")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Approve command received from user {update.effective_user.id}")
    if not context.args:
        logger.warning("No address provided for approve command")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Please provide an address to approve.")
        return

    address = ''.join(context.args)
    logger.info(f"Attempting to approve address: {address}")
    try:
        tx = nft_bridge.admin_set_bridging_approved(address, True)
        logger.info(f"Successfully approved {address}, tx: {tx.txn_hash}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Successfully approved {address}\nTx: {tx_hash_to_link(tx.txn_hash)}"
        )
    except Exception as e:
        logger.error(f"Failed to approve {address}: {str(e)}", exc_info=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Failed to approve {address}: {str(e)}"
        )

def main():
    logger.info("Starting NFT Bridge Bot")
    if env_vars.TG_BOT_TOKEN is None:
        logger.error("TG_BOT_TOKEN environment variable not set")
        raise ValueError("Please set the TG_BOT_TOKEN environment variable")

    logger.info("Initializing Telegram application")
    application = ApplicationBuilder().token(env_vars.TG_BOT_TOKEN).build()

    logger.debug("Setting up command handlers")
    start_handler = CommandHandler('start', start)
    bridge_handler = CommandHandler('bridge', bridge)
    approve_handler = CommandHandler('approve', approve)
    remint_handler = CommandHandler('remint', remint)

    application.add_handler(start_handler)
    application.add_handler(bridge_handler)
    application.add_handler(approve_handler)
    application.add_handler(remint_handler)

    logger.info("Starting bot polling")
    application.run_polling()

if __name__ == '__main__':
    main()
