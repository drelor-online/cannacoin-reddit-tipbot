import sys
from datetime import datetime
from peewee import fn
import tipper_functions
import text
from tipper_functions import (
    parse_text,
    add_history_record,
    add_new_account,
    account_tip,
    account_add_balance,
    account_subtract_balance,
    TipError,
    update_history_notes,
    parse_stroop_amount,
    send_pm,
    activate,
)
from tipper_rpc import (
    get_fee,
    get_balances,
    is_account_open,
    account_has_trustline,
    send_payment,
)
from text import WELCOME_CREATE, WELCOME_TIP, COMMENT_FOOTER, NEW_TIP, StatusResponse
from shared import (
    PROGRAM_MINIMUM,
    REDDIT,
    LOGGER,
    ACCOUNT,
    CURRENCY,
    CURRENCY_ISSUER,
    TIPBOT_OWNERS,
    to_stroop,
    from_stroop,
    Account,
    History,
    Subreddit,
    Transaction,
    NumberUtil
)


def handle_message(message):
    response = "not activated"
    parsed_text = parse_text(str(message.body))
    command = parsed_text[0].lower()
    username = str(message.author)
    # only activate if it's not an opt-out command
    if command != "opt-out":
        activate(username)
    # normal commands
    if command in ["help", "!help"]:
        LOGGER.info("Helping")
        subject = text.SUBJECTS["help"]
        response = handle_help(message)
    elif command in ["balance", "address"]:
        LOGGER.info("balance")
        subject = text.SUBJECTS["balance"]
        response = handle_balance(message)
    elif command in ["create", "register"]:
        LOGGER.info("Creating")
        subject = text.SUBJECTS["create"]
        response = handle_create(message)
    elif command in ["send", "withdraw"]:
        subject = text.SUBJECTS["send"]
        LOGGER.info("send via PM")
        response = handle_send(message)
        response = text.make_response_text(message, response)
    elif command == "history":
        LOGGER.info("history")
        subject = text.SUBJECTS["history"]
        response = handle_history(message)
    elif command == "silence":
        LOGGER.info("silencing")
        subject = text.SUBJECTS["silence"]
        response = handle_silence(message)
    elif command == "subreddit":
        LOGGER.info("subredditing")
        subject = text.SUBJECTS["subreddit"]
        response = handle_subreddit(message)
    elif command == "opt-out":
        LOGGER.info("opting out")
        response = handle_opt_out(message)
        subject = text.SUBJECTS["opt-out"]
    elif command == "opt-in":
        LOGGER.info("opting in")
        subject = text.SUBJECTS["opt-in"]
        response = handle_opt_in(message)
    elif command == "stats":
        LOGGER.info("stats")
        subject = text.SUBJECTS["stats"]
        response = handle_stats(message)        
    # a few administrative tasks
    elif command == "restart" and username in TIPBOT_OWNERS:
        add_history_record(
            username = username,
            action = "restart",
            comment_text = str(message.body)[:255],
            comment_or_message = "message",
            comment_id=message . name,
        )
        sys.exit()
    else:
        return None
    if len(response) > 0:
        message_recipient = username
        message_text = response + COMMENT_FOOTER
        send_pm(message_recipient, subject, message_text, bypass_opt_out=True)


def handle_balance(message):
    username = str(message.author)
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    try:
        account = Account.get(username=username)
        account_info = tipper_functions.account_info(username)
        results = account.balance
        response = text.BALANCE % (
            from_stroop(results), ACCOUNT, account_info["memo"]
        )
        return response        
    except Account.DoesNotExist:
        return text.NOT_OPEN


def handle_create(message):
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    username = str(message.author)
    try:
        account = Account.get(username=username)
        activate(username)
        response = text.ALREADY_EXISTS 
    except Account.DoesNotExist:
        account = add_new_account(username)
        response = WELCOME_CREATE % (ACCOUNT, account["memo"])
        add_history_record(
            username=username,
            comment_or_message="message",
            reddit_time=message_time,
            action="create",
            comment_id=message.name,
            comment_text=str(message.body)[:255],
        )            
    return response


def handle_help(message):
    response = text.HELP
    return response


def handle_history(message):
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    username = str(message.author)
    parsed_text = parse_text(str(message.body))
    num_records = 10
    # if there are more than 2 words, one of the words is a number for the number of records
    if len(parsed_text) >= 2:
        if parsed_text[1].lower() == "nan" or ("inf" in parsed_text[1].lower()):
            response = text.NAN
            return response
        try:
            num_records = int(parsed_text[1])
        except:
            response = text.NAN
            return response
    # check that it's greater than 50
    if num_records > 50:
        num_records = 50
    # check if the user is in the database
    try:
        acct = Account.get(username=username)
        response = "Here are your last %s historical records:\n\n" % num_records
        history = History.select(History.reddit_time, History.action, History.amount,
                    History.comment_id, History.notes, History.recipient_username, History.recipient_address).where(History.account == username).order_by(History.id.desc()).limit(num_records)
        for result in history:
            try:
                amount = result.amount
                if (result.action == "send") and amount:
                    amount = from_stroop(int(result.amount))
                    if result.notes == "sent to user":
                        response += (
                            "%s: %s | %s Poopstar to %s | reddit object: %s | %s\n\n"
                            % (
                                result.reddit_time.strftime("%Y-%m-%d %H:%M:%S"),
                                result.action,
                                amount,
                                result.recipient_username,
                                result.comment_id,
                                result.notes,
                            )
                        )
                    elif result.notes == "sent to address":
                        response += (
                            "%s: %s | %s Poopstar to %s | reddit object: %s | %s\n\n"
                            % (
                                result.reddit_time.strftime("%Y-%m-%d %H:%M:%S"),
                                result.action,
                                amount,
                                result.recipient_address,
                                result.comment_id,
                                result.notes,
                            )
                        )
                elif result.action == "receive":
                        response += (
                            "%s: %s | %s Poopstar | %s\n\n"
                            % (
                                result.reddit_time.strftime("%Y-%m-%d %H:%M:%S"),
                                result.action,
                                from_stroop(int(result.amount)),
                                result.notes,
                            )
                        )                      
                elif result.action == "send":
                    response += "%s: %s | reddit object: %s | %s\n\n" % (
                        result.reddit_time.strftime("%Y-%m-%d %H:%M:%S"),
                        result.action,
                        result.comment_id,
                        result.notes,
                    )
                else:
                    response += "%s: %s | %s | %s | %s\n\n" % (
                        result.reddit_time.strftime("%Y-%m-%d %H:%M:%S"),
                        result.action,
                        amount,
                        result.comment_id,
                        result.notes,
                    )
            except:
                pass
        return response        
    except Account.DoesNotExist:       
        response = text.NOT_OPEN
        return response


def handle_silence(message):
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    username = str(message.author)
    add_history_record(
        username = str(message.author),
        action = "silence",
        comment_or_message = "message",
        comment_id = message.name,
        reddit_time = message_time,
    )
    parsed_text = parse_text(str(message.body))
    if len(parsed_text) < 2:
        response = text.SILENCE["parse_error"]
        return response
    if parsed_text[1] == "yes":
        Account.update(silence=True).where(Account.username == username).execute()
        response = text.SILENCE["yes"]
    elif parsed_text[1] == "no":
        Account.update(silence=False).where(Account.username == username).execute()
        response = text.SILENCE["no"]
    else:
        response = text.SILENCE["yes_no"]
    return response


def handle_subreddit(message):
    parsed_text = parse_text(str(message.body))
    # If it is just the subreddit, return all the subreddits
    if len(parsed_text) <= 1:
        response = text.SUBREDDIT["all"]
        subreddits = Subreddit.select(Subreddit.subreddit, Subreddit.status, Subreddit.minimum)
        for result in subreddits:
            response += f"{result.subreddit}, {result.status}, {result.minimum}"
            response += "\n\n"
        return response
    # Return the subreddit stats
    if len(parsed_text) <= 2:
        response = text.SUBREDDIT["one"]
        try:
            result = Subreddit.select(Subreddit.subreddit, Subreddit.status, Subreddit.minimum).where(Subreddit.subreddit == parsed_text[1]).get()
            response += f"{result.subreddit}, {result.status}, {result.minimum}"
        except Subreddit.DoesNotExist:
            pass
        return response % parsed_text[1]
    # Check if the user is a moderator of the subreddit for the following commands.
    # All commands have 3 arguments from this point.
    if message.author not in REDDIT.subreddit(parsed_text[1]).moderator():
        return text.SUBREDDIT["not_mod"] % parsed_text[1]
    # change the subreddit minimum
    if parsed_text[2] in ["minimum", "min"]:
        try:
            float(parsed_text[3])
        except:
            return text.NAN % parsed_text[3]
        Subreddit.update(minimum = parsed_text[3]).where(Subreddit.subreddit == parsed_text[1]).execute()
        return text.SUBREDDIT["minimum"] % (parsed_text[1], parsed_text[3])
    if parsed_text[2] in ("disable", "deactivate"):
        # disable the bot
        try:
            Subreddit.delete().where(Subreddit.subreddit == parsed_text[1]).execute()
        except:
            pass
        return text.SUBREDDIT["deactivate"] % parsed_text[1]
    if parsed_text[2] in ("enable", "activate"):
        # if it's at least 4 words, set the status to that one
        if (len(parsed_text) > 3) and (parsed_text[3] in ["full", "silent"]):
            status = parsed_text[3]
        else:
            status = "full"
        # sql to change subreddit to that status
        try:
            subreddit = Subreddit.get(subreddit = parsed_text[1])
            Subreddit.update(status = status).where(Subreddit.subreddit == parsed_text[1]).execute()
        except Subreddit.DoesNotExist:
            subreddit = Subreddit(
                subreddit = parsed_text[1],
                reply_to_comments = True,
                footer = "",
                status = status
            )
            subreddit.save(force_insert=True)        
        return text.SUBREDDIT["activate"] % status
    # only 4 word commands after this point
    if len(parsed_text) < 4:
        return text.SUBREDDIT["error"]


def handle_stats(message):
    if not str(message.author).lower() in TIPBOT_OWNERS:
        return text.SUBREDDIT["not_maintainer"]
    off_chain_balance = Account.select(fn.SUM(Account.balance).alias('sum_balance')).get()
    response = f"Off-chain balance: {from_stroop(off_chain_balance.sum_balance):.2f} Poopstar  \n\n"
    main_account_balances = get_balances(ACCOUNT)
    if "ananos" in main_account_balances:
        balance = main_account_balances["ananos"]
        response += f"On-chain balance: {from_stroop(balance):.2f} Poopstar  \n\n"
    response += "\nTop accounts:  \n\n"
    accounts = Account.select(Account.username, Account.balance).order_by(Account.balance.desc()).limit(10)
    for idx, account in enumerate(accounts):
        response += f"{idx:02d}. {account.username} | {from_stroop(account.balance):.2f} Poopstar  \n\n"
    return response  



def handle_send(message):
    parsed_text = parse_text(str(message.body))
    username = str(message.author)
    message_time = datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    response = {"username": username}
    # check that there are enough fields (i.e. a username)
    if len(parsed_text) <= 2:
        response["status"] = StatusResponse.SEND_COMMAND_INCORRECT
        return response
    # Check for too many arguments
    if len(parsed_text) >= 4: 
        response["status"] = StatusResponse.SEND_COMMAND_TOO_MANY_ARGS
        return response
    # Check if sender has an account
    sender_info = tipper_functions.account_info(response["username"])
    if not sender_info:
        response["status"] = StatusResponse.NO_ACCOUNT
        return response
    # Convert the amount to stroop
    try:
        response["amount"] = parse_stroop_amount(parsed_text, response["username"])
    except TipError:
        response["status"] = StatusResponse.CANNOT_PARSE_AMOUNT
        response["amount"] = parsed_text[1]
        return response
    # Check if the amount is above the program minimum
    if response["amount"] < to_stroop(PROGRAM_MINIMUM):
        response["status"] = StatusResponse.BELOW_PROGRAM_MINIMUM
        return response
    # Check for sufficient funds
    if response["amount"] > sender_info["balance"]:
        response["status"] = StatusResponse.INSUFFICIENT_FUNDS
        return response
    recipient_text = parsed_text[2]
    # Catch invalid redditor AND address
    try:
        recipient_info = parse_recipient_username(recipient_text)
    except TipError as err:
        response["recipient"] = recipient_text
        response["status"] = StatusResponse.INVALID_USER_OR_ADDRESS
        return response
    entry_id = add_history_record(
        username = username,
        action = "send",
        comment_or_message = "message",
        comment_id = message.name,
        reddit_time = message_time,
        comment_text = str(message.body)[:255],
    )
    # Check if we can send to a Reddit user.
    if "username" in recipient_info.keys():
        if sender_info["username"].lower() == recipient_info["username"].lower():
            response["status"] = StatusResponse.CANNOT_SEND_TO_YOURSELF
            return response
        response["recipient"] = recipient_info["username"]
        recipient_name = recipient_info["username"]
        recipient_info = tipper_functions.account_info(recipient_name)
        response["status"] = StatusResponse.SENT_TO_EXISTING_USER
        if recipient_info is None: # Add new account
            recipient_info = tipper_functions.add_new_account(response["recipient"])
            if recipient_info is None:
                return text.TIP_CREATE_ACCT_ERROR
            response["status"] = StatusResponse.SENT_TO_NEW_USER
        elif not recipient_info["opt_in"]: # Existing account, check if opted out
            response["status"] = StatusResponse.USER_OPTED_OUT
            return response
        LOGGER.info(f"Tipping Poopstar: {sender_info['username']} {recipient_name} {response['amount']}")
        account_tip(sender_info["username"], recipient_name, response["amount"])
        History.update(notes = "sent to user", recipient_username = recipient_name, 
                       amount = str(response["amount"]), return_status="cleared").where(History.id == entry_id).execute()        
    # Check if we can send to a Stellar address.
    if "address" in recipient_info.keys():
        fee = get_fee()
        response["recipient"] = recipient_info["address"]
        main_account_balances = get_balances(ACCOUNT)
        if main_account_balances["xlm"] <= to_stroop(1.0) + fee:
            response["status"] = StatusResponse.NOT_ENOUGH_XLM
            return response
        if not account_has_trustline(recipient_info["address"], CURRENCY, CURRENCY_ISSUER):
            response["status"] = StatusResponse.NO_TRUSTLINE
            return response            
        LOGGER.info(f"Sending Poopstar: {response['amount']} {recipient_info['address']} {sender_info['memo']}")
        succeeded = send_payment(recipient_info["address"], response["amount"], sender_info["memo"], fee)
        if succeeded:
            response["status"] = StatusResponse.SENT_TO_ADDRESS
            account_subtract_balance(sender_info["username"], response["amount"])
            History.update(notes = "sent to address", recipient_username = None, recipient_address = recipient_info["address"],
                        amount = str(response["amount"]), return_status = "cleared").where(History.id == entry_id).execute()
            record = Transaction (
                time = datetime.utcnow(),
                source_account = ACCOUNT,
                destination_account = recipient_info["address"],
                amount = response["amount"],
                memo = sender_info["memo"],
                notes = "withdrawn"
            )      
            record.save()                  
        else:
            response["status"] = StatusResponse.SEND_TO_ADDRESS_FAILED 
        return response
    if response["status"] == StatusResponse.SENT_TO_NEW_USER:
        subject = text.SUBJECTS["first_tip"]
        message_text = (WELCOME_TIP % (NumberUtil.format_float(from_stroop(response["amount"])), ACCOUNT, sender_info["memo"]) + COMMENT_FOOTER)
        send_pm(recipient_info["username"], subject, message_text)
        return response
    else:
        if not recipient_info["silence"]:
            recipient_info = tipper_functions.account_info(recipient_name) # Update balance
            subject = text.SUBJECTS["new_tip"]
            message_text = (NEW_TIP % (NumberUtil.format_float(from_stroop(response["amount"])), from_stroop(recipient_info["balance"])) + COMMENT_FOOTER)
            send_pm(recipient_info["username"], subject, message_text)
        return response


def handle_opt_out(message):
    add_history_record(
        username = str(message.author),
        action = "opt-out",
        comment_or_message = "message",
        comment_id = message.name,
        reddit_time = datetime.utcfromtimestamp(message.created_utc),
    )
    Account.update(opt_in=False).where(Account.username == str(message.author)).execute()
    response = text.OPT_OUT
    return response


def handle_opt_in(message):
    add_history_record(
        username = str(message.author),
        action = "opt-in",
        comment_or_message = "message",
        comment_id = message.name,
        reddit_time = datetime.utcfromtimestamp(message.created_utc),
    )
    Account.update(opt_in=True).where(Account.username == str(message.author)).execute()
    response = text.OPT_IN
    return response


# Determines if a recipient is an Poopstar address or a redditor.
def parse_recipient_username(recipient_text):
    # remove the /u/ or u/
    if recipient_text[:3].lower() == "/u/":
        recipient_text = recipient_text[3:]
    elif recipient_text[:2].lower() == "u/":
        recipient_text = recipient_text[2:]    
    if len(recipient_text) == 56: # Length of a Stellar address
        # Check if account exists on the ledger
        success = is_account_open(recipient_text.upper())
        if success:
            return {"address": recipient_text.upper()}
    # A username may have been specified
    try:
        _ = getattr(REDDIT.redditor(recipient_text), "is_suspended", False)
        return {"username": recipient_text}
    except:
        raise TipError(
            "redditor does not exist",
            "Could not find redditor %s. Make sure you aren't writing or "
            "copy/pasting markdown." % recipient_text,
        )
