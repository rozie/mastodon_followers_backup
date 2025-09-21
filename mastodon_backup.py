#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import time
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Mastodon followed backup")

    parser.add_argument(
        "-u",
        "--url",
        required=True,
        type=str,
        default="https://mastodon.online/@rozie",
        help="URL account to be backed up",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        required=False,
        default=False,
        action="store_true",
        help="Provide verbose output",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        required=False,
        type=int,
        default=5,
        help="Timeout for fetching urls",
    )
    parser.add_argument(
        "-p",
        "--page",
        required=False,
        type=int,
        default=80,
        help="Page size for fetching followers with paginatnion",
    )
    args = parser.parse_args()
    return args


def parse_profile_url(profile_url):
    """
    Parses a Mastodon profile URL to get the instance and username.

    Args:
        profile_url (str): The full URL of the Mastodon profile.

    Returns:
        tuple: A tuple containing the instance and username, or (None, None).
    """
    try:
        parsed_url = urlparse(profile_url)
        instance = parsed_url.netloc
        # Username is typically the last part of the path, after the '@'
        username = parsed_url.path.strip("/").split("@")[-1]
        if not instance or not username:
            return None, None
        return instance, username
    except Exception as e:
        logger.error(
            f"Could not parse the provided URL. Please use a valid format (e.g., https://mastodon.online/@rozie). Error: {e}"
        )
        return None, None


def get_user_id(instance, username, timeout):
    """
    Fetches the user ID for a given username on a specific Mastodon instance.

    Args:
        instance (str): The domain of the Mastodon instance (e.g., 'mastodon.online').
        username (str): The username of the user (e.g., 'rozie').

    Returns:
        str: The user ID, or None if not found.
    """
    try:
        url = f"https://{instance}/api/v1/accounts/lookup?acct={username}"
        logger.debug(f"{url=}")
        response = requests.get(url, timeout)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json().get("id")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error looking up user ID for {username} on {instance}: {e}")
        return None
    except ValueError:
        logger.error(
            f"Error decoding JSON for user ID lookup: {username} on {instance}"
        )
        return None


def get_all_following(instance, user_id, timeout, page_size):
    """
    Fetches the complete list of accounts a user is following, handling pagination.

    Args:
        instance (str): The domain of the Mastodon instance.
        user_id (str): The ID of the user.

    Returns:
        list: A list of all account objects, or an empty list if an error occurs.
    """
    if not user_id:
        return []

    all_following = []
    # Set the initial URL. We can ask for the maximum limit of 80 per page.
    url = f"https://{instance}/api/v1/accounts/{user_id}/following?limit={page_size}"

    logger.debug(f"  Fetching following for user {user_id}...", end="", flush=True)

    while url:
        try:
            response = requests.get(url, timeout)
            # Check for rate limiting
            if response.status_code == 429:
                logger.debug("\nRate limited. Waiting for 60 seconds...")
                time.sleep(60)
                continue  # Retry the same URL

            response.raise_for_status()

            # Add the fetched accounts to our list
            data = response.json()
            if not data:
                break  # Stop if we get an empty response

            all_following.extend(data)

            # Check for the 'next' link in the Link header to paginate
            # The requests library handily parses this for us.
            if "next" in response.links:
                url = response.links["next"]["url"]
            else:
                # No more pages
                url = None

        except requests.exceptions.RequestException as e:
            logger.error(
                f"\nError fetching following list for user ID {user_id} on {instance}: {e}"
            )
            return []
        except ValueError:
            logger.error(
                f"\nError decoding JSON for following list: {user_id} on {instance}"
            )
            return []

    logger.debug(f" Found {len(all_following)} total.")
    return all_following


def main():
    args = parse_arguments()

    # set verbosity
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    initial_profile_url = args.url
    timeout = args.timeout
    page_size = args.page

    logger.debug(f"Starting with profile: {initial_profile_url}\n")

    # 1. Parse the initial URL to get the instance and username
    initial_instance, initial_username = parse_profile_url(initial_profile_url)
    if not initial_instance or not initial_username:
        logger.error("Couldn't find instance or username in URL")
        sys.exit(1)

    # 2. Get the user ID of the initial profile
    initial_user_id = get_user_id(initial_instance, initial_username, timeout)
    if not initial_user_id:
        logger.error(
            f"Could not find user ID for {initial_username} on {initial_instance}. Exiting."
        )
        sys.exit(1)

    # 3. Get the list of people the initial user is following
    logger.debug(f"Finding accounts followed by {initial_username}...")
    all_followed = get_all_following(
        initial_instance, initial_user_id, timeout, page_size
    )

    print(f"Found {len(all_followed)} followed by {initial_profile_url}:")

    for followed in all_followed:
        followed = followed.get("url")
        print(followed)


if __name__ == "__main__":
    main()
