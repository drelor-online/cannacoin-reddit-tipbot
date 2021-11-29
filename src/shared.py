import datetime
import os
import configparser
import praw
import logging
import sys
import stellar_sdk
from decimal import Decimal, getcontext
from hashlib import blake2b
from peewee import *
from playhouse.pool  import PooledMySQLDatabase

LOGGER = logging.getLogger("poopstar-reddit-tipbot")
LOGGER.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s;%(levelname)s;%(message)s", "%Y-%m-%d %H:%M:%S %z")
handler.setFormatter(formatter)
LOGGER.addHandler(handler)

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), "tipper.ini"))

# if we have a file, use it. Otherwise, load testing defaults
try:
    TIP_BOT_USERNAME = config["BOT"]["tip_bot_username"]
    PROGRAM_MINIMUM = float(config["BOT"]["program_minimum"])
    TIP_COMMANDS = config["BOT"]["tip_commands"].split(",")
    TIPBOT_OWNERS = config["BOT"]["tipbot_owners"].split(",")
    MAIN_SUB = config["BOT"]["main_sub"]
    PYTHON_COMMAND = config["BOT"]["python_command"]
    CURRENCY = config["BOT"]["currency"]
    CURRENCY_ISSUER = config["BOT"]["currency_issuer"]
    DEFAULT_FEE = config["BOT"]["default_fee"]
    DEFAULT_URL = config["NODE"]["default_url"]
    ACCOUNT = config["NODE"]["account"]
    SECRET = config["NODE"]["secret"]
    DATABASE_HOST = config["DB"]["database_host"]
    DATABASE_NAME = config["DB"]["database_name"]
    DATABASE_USER = config["DB"]["database_user"]
    DATABASE_PASSWORD = config["DB"]["database_password"]

except KeyError as e:
    LOGGER.error("Failed to read tipper.ini.")
    exit()


db = PooledMySQLDatabase(DATABASE_NAME, user=DATABASE_USER, password=DATABASE_PASSWORD, host=DATABASE_HOST, port=3306, max_connections=4)

              
try:
    REDDIT = praw.Reddit("bot1")
except Exception as err:
    raise err
    REDDIT = None

class NumberUtil(object):
    @classmethod
    def format_float(cls, in_number: float) -> str:
        """Format a float with un-necessary chars removed. E.g: 1.0000 == 1"""
        as_str = f"{in_number:.2f}".rstrip('0')            
        if as_str[len(as_str) - 1] == '.':
            as_str = as_str.replace('.', '')
        return as_str

def to_stroop(amount):
    amount = abs(float(amount))
    asStr = str(amount).split(".")
    wholeNumbers = int(asStr[0])
    if len(asStr[1]) > 2:
        asStr[1] = asStr[1][:2]
    asStr[1] = asStr[1].ljust(2, '0')
    decimals = int(asStr[1])
    return (wholeNumbers * (10**7)) + (decimals * (10 ** 5))

def from_stroop(amount):
    return float(amount) / (10 ** 7)

# Checks if the scripts should stop, based on the presence of a file.
def should_stop():
    if os.path.isfile("./stop"):
        return True
    return False

# Base Model
class BaseModel(Model):
	class Meta:
		database = db

class Account(BaseModel):
    created = DateTimeField(default=datetime.datetime.utcnow)
    updated = DateTimeField(default=datetime.datetime.utcnow)
    username = CharField(primary_key=True)
    memo = CharField(unique=True)
    balance = BigIntegerField(default=0)
    silence = BooleanField(default=False)
    active = BooleanField(default=False)
    opt_in = BooleanField(default=True)   
    class Meta:
        db_table = 'accounts'    

class History(BaseModel):
    account = ForeignKeyField(Account, related_name='history')
    action = CharField(default="unknown")
    reddit_time = DateTimeField(default=datetime.datetime.utcnow)
    sql_time = DateTimeField(default=datetime.datetime.utcnow)
    comment_or_message = CharField(null=True)
    recipient_username = CharField(null=True)
    recipient_address = TextField(null=True)
    amount = BigIntegerField(null=True)
    comment_id = CharField(null=True)
    comment_text = TextField(null=True)
    notes = CharField(null=True)
    return_status = CharField(null=True)

class Transaction(BaseModel):
    time = DateTimeField(default=datetime.datetime.utcnow)
    source_account = CharField(default="")
    destination_account = CharField(default="")
    hash = TextField(null=True)
    amount = BigIntegerField(default=0)
    memo = CharField(null=True)
    notes = CharField(null=True)
    class Meta:
        db_table = 'transactions'

class Message(BaseModel):
    username = CharField()
    subject = CharField()
    body = TextField(null=True)
    class Meta:
        db_table = 'messages'

class Subreddit(BaseModel):
    subreddit = CharField()
    reply_to_comments = BooleanField(default=True)
    footer = CharField(default="")
    status = CharField()
    minimum = CharField(default=PROGRAM_MINIMUM)
    class Meta:
        db_table = 'subreddits'

def create_db():
	with db.connection_context():
		db.create_tables([History, Message, Account, Subreddit, Transaction], safe=True)
create_db()


class SpamEntry:
  def __init__(self, date, requests):
    self.date = date
    self.requests = requests

SPAM_ENTRIES = dict()


# initiate the bot and all friendly subreddits
def get_subreddits():
    results = Subreddit.select()
    subreddits = [subreddit for subreddit in results]
    if len(subreddits) == 0:
        sub = Subreddit(
            subreddit = MAIN_SUB,
            reply_to_comments = True,
            status = "full",
            minimum = PROGRAM_MINIMUM
        )
        sub.save()
        results = Subreddit.select()
        subreddits = [subreddit for subreddit in results]
    subreddits_str = "+".join(result.subreddit for result in subreddits)
    return REDDIT.subreddit(subreddits_str)


# disable for testing
try:
    SUBREDDITS = get_subreddits()
except AttributeError:
    SUBREDDITS = None

class Validators():
    @classmethod
    def is_valid_address(cls, input_text: str) -> bool:
        """Return True if address is valid, false otherwise"""
        if input_text is None:
            return False
        return cls.validate_checksum_stellar(input_text)

    @staticmethod
    def is_valid_block_hash(block_hash: str) -> bool:
        if block_hash is None or len(block_hash) != 64:
            return False
        try:
            int(block_hash, 16)
        except ValueError:
            return False
        return True

    @staticmethod
    def validate_checksum_stellar(address: str) -> bool:
        try:
            stellar_sdk.account.Account(account_id=address, sequence=0)
            return True

        except stellar_sdk.exceptions.Ed25519PublicKeyInvalidError:
            return False

