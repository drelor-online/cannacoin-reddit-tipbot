import time

from time import sleep

import shared
from shared import REDDIT, SUBREDDITS, LOGGER, should_stop
from message_functions import handle_message
from tipper_functions import parse_action, handle_transactions
from comment_functions import handle_comment


# how often we poll for new transactions
CYCLE_TIME = 6

LOGGER.info("Starting tip bot")

def main_loop():
    global SUBREDDITS
    actions = {
        "message": handle_message,
        "comment": handle_comment,
        "ignore": lambda x: None,
        "replay": lambda x: None,
        None: lambda x: None,
    }
    subreddit_timer = time.time()
    sleep_timer = time.time()
    sleep_time = CYCLE_TIME - (time.time() - sleep_timer)
    previous_comments = {comment for comment in SUBREDDITS.comments()}
    previous_messages = {message for message in REDDIT.inbox.all(limit=25)}
    previous_all = previous_comments.union(previous_messages)

    while True:
        if should_stop():
            exit(0)
        if sleep_time > 0:
            sleep(sleep_time)
        sleep_timer = time.time()
        # Check for new comments and messages
        updated_comments = {comment for comment in SUBREDDITS.comments()}
        updated_messages = {message for message in REDDIT.inbox.all(limit=25)}
        updated_all = updated_comments.union(updated_messages)
        new = updated_all - previous_all
        previous_all = updated_all
        for action_item in new:
            action = parse_action(action_item)
            actions[action](action_item)
            # Refresh subreddit status every 5 minutes
            if time.time() - subreddit_timer > 300:
                subreddit_timer = time.time()
                shared.SUBREDDITS = shared.get_subreddits()
                SUBREDDITS = shared.SUBREDDITS
        # Handle incoming transactions
        handle_transactions()

if __name__ == "__main__":
    main_loop()
