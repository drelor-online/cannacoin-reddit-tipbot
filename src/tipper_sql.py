import time
from datetime import datetime
from shared import PROGRAM_MINIMUM, db, Subreddit, Account

@db.connection_context()
def add_subreddit(
    subreddit,
    reply_to_comments=True,
    footer="",
    status="full",
    minimum=PROGRAM_MINIMUM,
):
    sub = Subreddit(
        subreddit = subreddit,
        reply_to_comments = reply_to_comments,
        footer = footer,
        status = status,
        minimum = minimum
    )
    sub.save(force_insert=True)


@db.connection_context()
def modify_subreddit(subreddit, status):
    Subreddit.update(status=status).where(Subreddit.subreddit == subreddit).execute()


@db.connection_context()
def rm_subreddit(subreddit):
    Subreddit.delete().where(Subreddit.subreddit == subreddit).execute()


@db.connection_context()
def subreddits():
    results = Subreddit.select()
    for result in results:
        print(f"Subreddit: {result.subreddit}, status: {result.status}")
