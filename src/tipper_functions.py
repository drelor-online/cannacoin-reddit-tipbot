from datetime import datetime
from shared import (
    TIP_BOT_USERNAME,
    LOGGER,
    TIP_COMMANDS,
    db,
    from_stroop,
    to_stroop,
    History,
    Account,
    ACCOUNT,
    Transaction,
    Message,
    REDDIT,
    NumberUtil,
    SpamEntry,
    SPAM_ENTRIES
)
from text import SUBJECTS, COMMENT_FOOTER, StatusResponse, SEND_TEXT
import text
import re
import shared
import tipper_rpc


def add_history_record(
    username=None,
    action="unknown",
    comment_or_message=None,
    recipient_username=None,
    amount=None,
    comment_id=None,
    notes=None,
    reddit_time=None,
    comment_text=None,
):
    try:
        account = Account.get(Account.username == str(username))
    except Account.DoesNotExist:
        LOGGER.exception(f"Tried to add a history record for an unknown user: {username}")
        return False
    if action is None:
        action = "unknown"
    if reddit_time is None:
        reddit_time=datetime.utcnow()
    history = History(
        account=account,
        action=action,
        comment_or_message=comment_or_message,
        recipient_username=recipient_username,
        amount=amount,
        comment_id=comment_id,
        notes=notes,
        reddit_time=reddit_time,
        comment_text=comment_text        
    )
    if history.save() < 1:
        LOGGER.error(f"Failed saving history item {username}")
        return False
    return history.id


def make_graceful(func):
    """
    Wrapper for inherited GracefulList methods that otherwise return a list
    100% unncecessary, only used for list __add__ at the moment
    """
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        if isinstance(res, list):
            return GracefulList(func(*args, **kwargs))
        else:
            return res
    return wrapper


class TipError(Exception):
    """
    General tiperror exception
    """
    def __init__(self, sql_text, response):
        self.sql_text = sql_text
        self.response = response


class GracefulList(list):
    """
    GracefulList is a list that returns None if there is an index error.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def __getitem__(self, name):
        try:
            if isinstance(name, int):
                return super().__getitem__(name)
            return GracefulList(super().__getitem__(name))
        except IndexError:
            return None
    @make_graceful
    def __add__(self, other):
        return super().__add__(other)


def parse_text(text):
    text = text.strip(" ")
    return GracefulList(text.lower().replace("\\", "").replace("\n", " ").split(" "))


def add_new_account(username):
    username = str(username)
    memo = username.lower()
    account = Account(
        username = username,
        memo = memo,
        balance = 0,
        silence = False,
        active = False,
        opt_in = True
    )
    account.save(force_insert=True)
    return {
        "username": username,
        "memo": memo,
        "silence": False,
        "balance": 0,
        "account_exists": True,
    }


def activate(username):
    Account.update(active=True).where(Account.username == str(username)).execute()


def allowed_request(username, seconds=30, num_requests=4):
    if str(username) in SPAM_ENTRIES:
        stats = SPAM_ENTRIES[str(username)]        
        time_passed = (datetime.utcnow() - stats.date).seconds
        if time_passed <= seconds and stats.requests >= num_requests:
            return False
        if time_passed > seconds:
            stats.date = datetime.utcnow()
            stats.requests = 1
        else:
            stats.requests += 1
    else:
        stats = SpamEntry (datetime.utcnow(), 1)
        SPAM_ENTRIES[str(username)] = stats
    # Delete first key from dict if possible
    first_key = next(iter(SPAM_ENTRIES))
    oldest_time = (datetime.utcnow() - SPAM_ENTRIES[first_key].date).seconds
    if oldest_time > seconds:
        del SPAM_ENTRIES[first_key]

    return True


def memo_to_username(memo):
    try:
        account = Account.select().where(Account.memo == str(memo)).get()
    except Account.DoesNotExist:
        return None
    return account.username

def account_info(username):
    """
    Pulls the address, private key and balance from a user
    :param username: string - redditors username
    :return: dict - name, address, private_key, balance
    """
    foundAccount = True
    try:
        account = Account.select().where(Account.username == str(username)).get()
    except Account.DoesNotExist:
        foundAccount = False
    if foundAccount:
        return {
            "username": account.username,
            "memo": account.memo,
            "silence": account.silence,
            "balance": account.balance,
            "account_exists": True,
            "opt_in": account.opt_in,
        }
    return None

@db.atomic()
def account_tip(from_username, to_username, amount):
    Account.update(balance = Account.balance - amount).where(Account.username == from_username).execute()
    Account.update(balance = Account.balance + amount).where(Account.username == to_username).execute()

def account_add_balance(username, amount):
    Account.update(balance = Account.balance + amount).where(Account.username == username).execute()
    return None

def account_subtract_balance(username, amount):
    Account.update(balance = Account.balance - amount).where(Account.username == username).execute()
    return None


def update_history_notes(id, text):
    History.update(notes = text).where(History.id == id).execute()


def send_pm(username, subject, body, bypass_opt_out = False):
    opt_in = True
    # If there is not a bypass to opt in, check the status
    try:
        account = Account.get(Account.username == str(username))
        opt_in = account.opt_in
    except Account.DoesNotExist:        
        pass
    # if the user has opted in, or if there is an override to send the PM even if they have not
    if opt_in or bypass_opt_out:
        msg = Message(
            username = str(username),
            subject = subject,
            body = body
        )
        msg.save()


def parse_stroop_amount(parsed_text, username = None):
    """
    Given some parsed command text, converts the units to stroop
    :param parsed_text:
    :param username: required if amount is 'all'
    :return:
    """
    # check if the amount is 'all'. This will convert it to the proper int
    if parsed_text[1].lower() == "all":
        try:
            account = Account.select(Account.balance).where(Account.username == str(username)).get()
            balance = account.balance
            return balance
        except Account.DoesNotExist:
            raise (TipError(None, text.NOT_OPEN))
    amount = parsed_text[1].lower()    
    # before converting to a number, make sure the amount doesn't have nan or inf in it
    if amount == "nan" or ("inf" in amount):
        raise TipError(
            None,
            f"Could not read your tip or send amount. Is '{parsed_text[1]}' a number?",
        )
    else:
        try:
            amount = to_stroop(float(amount))
        except:
            raise TipError(
                None,
                f"Could not read your tip or send amount. Is '{amount}' a number, or is the "
                "currency code valid?",
            )
    return amount


def message_in_database(message):
    exists = History.select().where(History.comment_id == message.name).count()
    if exists > 0:
        LOGGER.info("Found previous messages for %s: " % message.name)
        return True
    return False


def parse_action(action_item):
    if action_item is not None:
        parsed_text = parse_text(str(action_item.body).lower())
    else:
        return None
    if message_in_database(action_item):
        return "replay"
    elif not allowed_request(action_item.author):
        return "ignore"
    # Check if it's a non-username post and if it has a tip or donate command
    # t1_: comment designation
    elif action_item.name.startswith("t1_") and bool(
        {parsed_text[0], parsed_text[-2], parsed_text[-3]}
        & (
            set(TIP_COMMANDS).union(
                {"/u/%s" % TIP_BOT_USERNAME, "u/%s" % TIP_BOT_USERNAME}
            )
        )
    ):
        LOGGER.info(f"Comment: {action_item.author} - " f"{action_item.body[:20]}")
        return "comment"
    # Otherwise, lets parse the message.
    # t4_: message/username
    elif action_item.name.startswith("t4_"):
        LOGGER.info(f"Comment: {action_item.author} - " f"{action_item.body[:20]}")
        return "message"
    return None

def handle_transactions():
    transactions = tipper_rpc.get_incoming_transactions()
    for transaction in transactions:
        if (datetime.utcnow() - transaction["date"]).days > 7:
            break # Don't process old transactions
        try:
            record = Transaction.get(Transaction.hash == transaction['hash'])
            # If this transaction exists in the database, older transactions are assumed to exist as well.
            break
        except Transaction.DoesNotExist:    
            # Get payments associated with the transaction.    
            payments = tipper_rpc.get_transaction_payments(transaction['hash'])
            amount = 0
            for payment in payments:
                if payment["to"] == ACCOUNT and payment["asset"] == "ananos":
                    amount += payment["amount"]
            record = Transaction (
                time = transaction['date'],
                source_account = transaction['source_account'],
                destination_account = ACCOUNT,
                hash = transaction['hash'],
                amount = amount,
                memo = transaction['memo'],
            )
            record.save()
            fee = tipper_rpc.get_fee()            
            # Don't process a transaction with zero amount of Ananos.
            if amount <= 0:
                continue
            # Check for memo
            if not transaction["memo"]:
                LOGGER.info(f"Returning deposited Ananos, no user specified: {transaction['hash']} {transaction['source_account']} {amount}")
                tipper_rpc.send_payment(transaction["source_account"], amount, "no user specified", fee)            
                Transaction.update(notes = "no user specified").where(Transaction.hash == transaction['hash']).execute()
                continue
            # Get recipient username
            memo_name = transaction["memo"].lower()
            if memo_name[:3] == "/u/":
                memo_name = memo_name[3:]
            elif memo_name[:2] == "u/":
                memo_name = memo_name[2:]    
            recipient_name = memo_to_username(memo_name)                
            try:
                _ = getattr(REDDIT.redditor(recipient_name), "is_suspended", False)                
            except:
                LOGGER.info(f"Returning deposited Ananos, user unknown: {transaction['hash']} {transaction['source_account']} {amount}  {transaction['memo']}")
                tipper_rpc.send_payment(transaction["source_account"], amount, "unknown user specified", fee)            
                Transaction.update(notes = "unknown user").where(Transaction.hash == transaction['hash']).execute()
                continue
            # Get account info            
            recipient_info = account_info(recipient_name)            
            if recipient_info is None: 
                LOGGER.info(f"Returning deposited Ananos, user has no account: {transaction['hash']} {transaction['source_account']} {amount}  {transaction['memo']}")
                tipper_rpc.send_payment(transaction["source_account"], amount, "user has no account", fee)            
                Transaction.update(notes = "user has no account").where(Transaction.hash == transaction['hash']).execute()
                continue
            # Add the funds
            account_add_balance(recipient_info['username'], amount)            
            Transaction.update(notes = "deposited").where(Transaction.hash == transaction['hash']).execute()
            if not recipient_info["silence"]:
                subject = text.SUBJECTS["deposit"]
                message_text = SEND_TEXT[StatusResponse.DEPOSIT] % (NumberUtil.format_float(from_stroop(amount)), recipient_info["username"]) + COMMENT_FOOTER
                send_pm(recipient_info["username"], subject, message_text)          
                add_history_record(
                    username = recipient_info['username'],
                    action = "receive",
                    amount = amount,
                    comment_or_message = "message",
                    comment_text = transaction['source_account'],
                    notes = "received from address"
                )                      
