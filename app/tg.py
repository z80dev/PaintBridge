import dotenv
dotenv.load_dotenv()
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from ape.logging import logger as ape_logger, LogLevel
from .config import env_vars
from .nft_bridge import NFTBridge, AirdropUnit
from .utils import has_too_many_nfts, has_too_many_owners, last_sale_within_six_months

# Configure logging with more detailed format
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Set up file handler
file_handler = logging.FileHandler('nft_bridge_bot.log')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

ape_logger.set_level(LogLevel.ERROR)

logger.info("Initializing NFT Bridge!")
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
    skip_authorizer=False
)
logger.info("NFT Bridge initialized successfully")

def tx_hash_to_link(tx_hash: str) -> str:
    env = env_vars.FLASK_ENV
    logger.debug(f"Generating transaction link for hash {tx_hash} in {env} environment")
    if env == 'prod':
        return f"https://sonicscan.org/tx/{tx_hash}"
    return f"https://testnet.soniclabs.com/tx/{tx_hash}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.effective_chat is not None
    assert update.effective_user is not None
    logger.info(f"Start command received from user {update.effective_user.id}")
    msg_str = """Hello! I can bridge NFTs for you. Collection requirements:
- Must be verified
- Less than 11,000 total NFTs
- Less than 11,000 owners
- Must have had a sale in the last 6 months
- Must have been approved for bridging (by collection owner or admin)
Use /approve <address> to approve a collection for bridging
Use /bridge <address> to bridge a collection
Use /clear <address> to clear bridged storage (admin only)
Optional parameters:
- owner:<address> - Override the owner address
- override - Skip requirement checks"""
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg_str)
    logger.debug("Start message sent successfully")

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

    # if not last_sale_within_six_months(collection_data):
    #     logger.warning(f"Collection {addr} has no recent sales")
    #     await context.bot.send_message(chat_id=update.effective_chat.id,
    #                                  text=f"Collection has not been sold in 6 months: {addr}")
    #     return False

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
        logger.debug(f"ERC721 Params: {addr}, {original_owner}, {name}, {symbol}, {base_uri}, {extension}, {royalty_data['recipient']}, {royalty_data['fee']}")
        deployment_tx = nft_bridge.deploy_721(
            addr, original_owner, name, symbol, base_uri, extension,
            royalty_data["recipient"], royalty_data["fee"]
        )
        logger.info(f"ERC721 deployment transaction: {deployment_tx.txn_hash}")
        return deployment_tx, base_uri
    else:
        logger.info("Deploying ERC1155 contract")
        name = nft_bridge.get_collection_name(addr)
        deployment_tx = nft_bridge.deploy_1155(
            addr, original_owner, royalty_data["recipient"], royalty_data["fee"], name
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

    # Get input address (only accept original address for bridge command)
    input_addr = context.args[0]
    logger.info(f"Starting bridge process for address: {input_addr}")

    if len(context.args) > 1:
        logger.info(f"Additional arguments provided: {context.args[1:]}")

    # Parse additional arguments
    override_requirements = False
    owner_override = None

    for arg in context.args[1:]:
        if arg == "override":
            override_requirements = True
        elif arg.startswith("owner:"):
            owner_override = arg.split(":")[1]
            logger.info(f"Owner override provided: {owner_override}")

    # Check if this is a bridged address
    original_from_bridged = nft_bridge.get_original_address(input_addr)
    if original_from_bridged:
        # This is a bridged address, so let's use the original address instead
        logger.info(f"Input address {input_addr} is a bridged address, using original address {original_from_bridged}")
        addr = original_from_bridged
        bridged_addr = input_addr
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                    text=f"Already bridged. Original: {addr}, Bridged: {bridged_addr}. Use /remint {addr} to remint tokens to current holders.")
        return
    else:
        addr = input_addr
    
    if bridged_addr := nft_bridge.get_bridged_address(addr):
        logger.info(f"Collection {addr} already bridged to {bridged_addr}")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                    text=f"Already bridged to {bridged_addr}. Use /remint {addr} to remint tokens to current holders.")
        return

    if not nft_bridge.is_collection_approved(addr):
        logger.warning(f"Collection {addr} not approved for bridging")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                    text=f"Collection not approved for bridging: {addr}")
        return

    collection_data = nft_bridge.get_collection_data_api(addr)
    if not override_requirements and not await validate_collection(update, context, addr, collection_data):
        logger.warning(f"Collection validation failed for {addr}")
        return

    logger.info(f"Starting bridging process for collection {addr}")
    msg = f"Bridging collection {addr}\n"
    if owner_override:
        msg += f"Owner override: {owner_override}\n"
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=msg)

    holders = nft_bridge.get_holders_via_api(addr)
    airdrop_units = list(holders.values())
    is721 = airdrop_units[0].is721
    logger.info(f"Collection type: {'ERC721' if is721 else 'ERC1155'}, holders: {len(holders)}")

    royalty_data = await get_royalty_info(addr)
    await send_royalty_info(update, context, royalty_data)

    original_owner = nft_bridge.get_collection_owner(addr)
    logger.info(f"Original collection owner: {original_owner}")

    original_owner = owner_override or nft_bridge.get_collection_owner(addr)
    logger.info(f"Using owner address: {original_owner} {'(override)' if owner_override else '(original)'}")

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

    summary_msg = f"Collection bridged successfully: {addr}\n" \
                    f"Original address: {addr}\n" \
                    f"Bridged address: {bridged_address}\n" \
                    f"ERC721: {is721}\n" \
                    f"Original owner: {original_owner}\n" \
                    f"Royalty recipient: {royalty_data['recipient']}\n" \
                    f"Royalty fee: {royalty_data['fee']}\n" \
                    f"Total holders: {len(holders)}\n" \
                    f"Total airdrop txs: {len(airdrop_txs)}\n"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=summary_msg)


async def remint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Remint command received from user {update.effective_user.id}")
    assert update.effective_chat is not None

    if not context.args:
        logger.warning("No address provided for remint command")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Please provide an address to remint.")
        return

    # Get input address and handle both original and bridged addresses
    input_addr = context.args[0]
    logger.info(f"Starting remint process for input address: {input_addr}")
    
    # Resolve to original address - works with either original or bridged address
    original_addr = nft_bridge.resolve_original_address(input_addr)
    if not original_addr:
        logger.warning(f"Could not resolve to a valid original address: {input_addr}")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Collection not yet bridged. Use /bridge {input_addr} first.")
        return
        
    # Get the bridged address from the resolved original address
    bridged_addr = nft_bridge.get_bridged_address(original_addr)
    if not bridged_addr:
        logger.warning(f"Collection {original_addr} not yet bridged")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Collection not yet bridged. Use /bridge {input_addr} first.")
        return

    override_requirements = len(context.args) > 1 and context.args[1] == "override"

    collection_data = nft_bridge.get_collection_data_api(original_addr)
    if not override_requirements and not await validate_collection(update, context, original_addr, collection_data):
        logger.warning(f"Collection validation failed for remint of {original_addr}")
        return

    holders = nft_bridge.get_holders_via_api(original_addr)
    airdrop_units = list(holders.values())
    is721 = airdrop_units[0].is721
    logger.info(f"Reminting for {len(holders)} holders")

    airdrop_txs = await handle_airdrop(update, context, bridged_addr, airdrop_units)
    airdrop_tx_links = [tx_hash_to_link(tx.txn_hash) for tx in airdrop_txs]
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Remint txs:\n{'\n'.join(airdrop_tx_links)}")

    await handle_uris(update, context, original_addr, bridged_addr, is721, "")
    logger.info(f"Remint process completed successfully for {original_addr}")

async def reclaim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Reclaim command received from user {update.effective_user.id}")
    assert update.effective_chat is not None

    if not context.args:
        logger.warning("No address provided for reclaim command")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Please provide an address to reclaim.")
        return

    # Get input address and handle both original and bridged addresses
    input_addr = context.args[0]
    logger.info(f"Starting reclaim process for input address: {input_addr}")
    
    # Resolve to original address - works with either original or bridged address
    original_addr = nft_bridge.resolve_original_address(input_addr)
    if not original_addr:
        logger.warning(f"Could not resolve to a valid original address: {input_addr}")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Collection not yet bridged. Use /bridge {input_addr} first.")
        return
        
    # Get the bridged address from the resolved original address
    bridged_addr = nft_bridge.get_bridged_address(original_addr)
    if not bridged_addr:
        logger.warning(f"Collection {original_addr} not yet bridged")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Collection not yet bridged. Use /bridge {input_addr} first.")
        return

    override_requirements = len(context.args) > 1 and context.args[1] == "override"
    collection_data = nft_bridge.get_collection_data_api(original_addr)
    if not override_requirements and not await validate_collection(update, context, original_addr, collection_data):
        logger.warning(f"Collection validation failed for reclaim of {original_addr}")
        return

    holders = nft_bridge.get_holders_via_api(original_addr)
    if not holders:
        logger.warning(f"No holders found for {original_addr}")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"No holders found for {original_addr}.")
        return

    is721 = list(holders.values())[0].is721
    admin_address = nft_bridge.deployer.address

    admin_airdrop_units = []

    if is721:
        current_token_ids = []
        for unit in holders.values():
            if len(current_token_ids) < 25:
                admin_airdrop_units.append(AirdropUnit(admin_address, current_token_ids.copy(), [], is721=True))
                current_token_ids = []
            current_token_ids.extend(unit.token_ids)
        if len(current_token_ids) > 0:
            admin_airdrop_units.append(AirdropUnit(admin_address, current_token_ids.copy(), [], is721=True))
    else:
        for unit in holders.values():
            admin_airdrop_units.append(AirdropUnit(admin_address, unit.token_ids, unit.amounts, is721=False))

    airdrop_txs = await handle_airdrop(update, context, bridged_addr, admin_airdrop_units)
    airdrop_links = [tx_hash_to_link(tx.txn_hash) for tx in airdrop_txs]
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Reclaim txs:\n{'\n'.join(airdrop_links)}")

    logger.info(f"Reclaim completed for {original_addr}")

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

async def seturis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"SetURIs command received from user {update.effective_user.id}")
    assert update.effective_chat is not None

    if not context.args or len(context.args) < 2:
        logger.warning("Invalid arguments for seturis command")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Usage: /seturis <address> <start_index>"
        )
        return

    # Get input address and handle both original and bridged addresses
    input_addr = context.args[0]
    try:
        start_index = int(context.args[1])
    except ValueError:
        logger.warning(f"Invalid start index: {context.args[1]}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Invalid start index. Must be an integer."
        )
        return

    logger.info(f"Starting URI set process for input address: {input_addr} from index {start_index}")
    
    # Resolve to original address - works with either original or bridged address
    original_addr = nft_bridge.resolve_original_address(input_addr)
    if not original_addr:
        logger.warning(f"Could not resolve to a valid original address: {input_addr}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Collection not yet bridged. Use /bridge {input_addr} first."
        )
        return
        
    # Get the bridged address from the resolved original address
    bridged_address = nft_bridge.get_bridged_address(original_addr)
    if not bridged_address:
        logger.warning(f"Collection {original_addr} not yet bridged")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Collection not yet bridged. Use /bridge {input_addr} first."
        )
        return

    # uris = nft_bridge.get_token_uris_via_erc721enumerable(original_addr)
    # nft_bridge.set_token_uris_from_tuples(bridged_address, uris)
    # logger.info(f"Successfully set URIs for {original_addr} from index {start_index}")
    # return

    try:
        is721 = not nft_bridge.is_erc1155(original_addr)  # Check if ERC1155

        uris = nft_bridge.get_token_uris(original_addr, is721=is721)
        logger.info(f"Total URIs: {len(uris)}")
        logger.info(f"{uris}")
        uris = uris[start_index:]
        logger.info("calling set_token_uris")
        uri_txs = nft_bridge.set_token_uris(bridged_address, uris, start_from=start_index)

        if not uri_txs:
            logger.info("No URIs to set")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="No URIs to set for this collection."
            )
            return

        uri_tx_links = [tx_hash_to_link(tx.txn_hash) for tx in uri_txs]
        response_msg = f"URI txs starting from {start_index}:\n{'\n'.join(uri_tx_links)}"
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response_msg
        )
        logger.info(f"Successfully set URIs for {original_addr} from index {start_index}")

    except Exception as e:
        logger.error(f"Failed to set URIs: {str(e)}", exc_info=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Failed to set URIs: {str(e)}"
        )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Clear command received from user {update.effective_user.id}")
    assert update.effective_chat is not None

    if not context.args:
        logger.warning("No address provided for clear command")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Please provide an address to clear bridged storage.")
        return

    # Get input address and handle both original and bridged addresses
    input_addr = context.args[0]
    logger.info(f"Starting clear process for input address: {input_addr}")
    
    try:
        # Resolve to original address - works with either original or bridged address
        original_addr = nft_bridge.resolve_original_address(input_addr)
        if not original_addr:
            logger.warning(f"Could not resolve to a valid original address: {input_addr}")
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=f"Collection not bridged: {input_addr}")
            return
            
        # Get the bridged address from the resolved original address
        bridged_addr = nft_bridge.get_bridged_address(original_addr)
        if not bridged_addr:
            logger.warning(f"Collection {original_addr} not bridged")
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=f"Collection not bridged: {input_addr}")
            return

        tx = nft_bridge.clear_bridged_storage(original_addr)
        logger.info(f"Successfully cleared bridged storage for {original_addr}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Successfully cleared bridged storage for {original_addr}\nTx: {tx_hash_to_link(tx.txn_hash)}"
        )

    except Exception as e:
        logger.error(f"Failed to clear bridged storage for {input_addr}: {str(e)}", exc_info=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Failed to clear bridged storage: {str(e)}"
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
    reclaim_handler = CommandHandler('reclaim', reclaim)
    seturis_handler = CommandHandler('seturis', seturis)  # Add this line
    clear_handler = CommandHandler('clear', clear)  # Add this line

    application.add_handler(start_handler)
    application.add_handler(bridge_handler)
    application.add_handler(approve_handler)
    application.add_handler(remint_handler)
    application.add_handler(reclaim_handler)
    application.add_handler(seturis_handler)
    application.add_handler(clear_handler)  # Add this line

    logger.info("Starting bot polling")
    application.run_polling()

if __name__ == '__main__':
    main()
