#!/usr/bin/env python3
from ape import networks
import os
import re
import time
import logging

flask_env = os.getenv("FLASK_ENV")

logger = logging.getLogger(__name__)

def chunk(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


def target_chain_context(func):
    def wrapper(*args, **kwargs):
        if flask_env == "development":
            with networks.ethereum.local.use_provider("foundry"):
                return func(*args, **kwargs)
        elif flask_env == "testnet":
            with networks.fantom.sonictest.use_provider("node"):
                return func(*args, **kwargs)
        elif flask_env == "prod":
            with networks.fantom.sonic.use_provider("node"):
                return func(*args, **kwargs)

    return wrapper


def source_chain_context(func):
    def wrapper(*args, **kwargs):
        with networks.fantom.opera.use_provider("alchemy"):
            return func(*args, **kwargs)

    return wrapper


def parse_url(url: str) -> tuple[str, str, str] | None:
    """
    Parse a URL that ends in a number with an optional .json extension.

    Args:
        url: String URL to parse

    Returns:
        Tuple of (base_url, number, extension) if URL matches pattern,
        where extension will be empty string if not present.
        Returns None if URL doesn't match pattern.

    Examples:
        >>> parse_url("https://foo.com/1")
        ('https://foo.com/', '1', '')
        >>> parse_url("https://foo.com/42.json")
        ('https://foo.com/', '42', '.json')
        >>> parse_url("https://foo.com/not-a-number")
        None
    """
    pattern = r"^(.+/)(\d+)(\.json)?$"
    match = re.match(pattern, url)

    if match:
        base_url, number, extension = match.groups()
        return (base_url, number, extension or "")

    return None

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
