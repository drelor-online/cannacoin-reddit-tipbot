import datetime
from text import (
    COMMENT_FOOTER, 
    SUBJECTS, 
    NEW_TIP,
    WELCOME_TIP,
    COMMENT_FOOTER,
    make_response_text, 
    StatusResponse
)
from shared import (
    TIP_COMMANDS,
    PROGRAM_MINIMUM,
    LOGGER,
    TIP_BOT_USERNAME,
    ACCOUNT,
    from_stroop,
    to_stroop,
    Message,
    Subreddit,
    NumberUtil,
    History
)
from tipper_functions import (
    add_history_record,
    account_info,
    add_new_account,
    send_pm,
    parse_text,
    account_tip,
    TipError,
    parse_stroop_amount,
)

# handles tip commands on subreddits
def handle_comment(message):
    response = send_from_comment(message)
    response_text = make_response_text(message, response)
    # Check if subreddit is untracked or silent. If so, PM the users.
    if response["subreddit_status"] in ["silent", "untracked", "hostile"]:
        message_recipient = str(message.author)
        if response["status"] < 100:
            subject = SUBJECTS["success"]
        else:
            subject = SUBJECTS["failure"]
        message_text = response_text + COMMENT_FOOTER
        msg = Message(
            username = message_recipient,
            subject = subject,
            body = message_text
        )
        msg.save()
    else:
        message.reply(response_text + COMMENT_FOOTER)


# Extracts send command information from a PM command
# For error codes, see text.py.
def send_from_comment(message):
    parsed_text = parse_text(str(message.body))
    response = {"username" : str(message.author)}
    message_time = datetime.datetime.utcfromtimestamp(
        message.created_utc
    )  # time the reddit message was created
    # Command at start of comment: don't do anything if the first word is a tip command or username
    if (parsed_text[0] in [f"/u/{TIP_BOT_USERNAME}", f"u/{TIP_BOT_USERNAME}"]) or (
        parsed_text[0] in TIP_COMMANDS
    ):
        pass
    # Command at end of comment: f the second to last is a username or tip command, redifine parsed text
    elif (parsed_text[-2] in [f"/u/{TIP_BOT_USERNAME}", f"u/{TIP_BOT_USERNAME}"]) or (
        parsed_text[-2] in TIP_COMMANDS
    ):
        parsed_text = parsed_text[-2:]
    else: # No command found
        response["status"] = 999
        return   
    # Before we can do anything, check the subreddit status for generating the response
    response["subreddit"] = str(message.subreddit).lower()
    try:
        sr = Subreddit.select(Subreddit.status, Subreddit.minimum).where(Subreddit.subreddit == response["subreddit"]).get()
        response["subreddit_status"] = sr.status
        response["subreddit_minimum"] = sr.minimum            
    except Subreddit.DoesNotExist:
        response["subreddit_status"] = "untracked"
        response["subreddit_minimum"] = "1"        
    # Check if amount is specified
    if parsed_text[0] in TIP_COMMANDS and len(parsed_text) <= 1:
        response["status"] = StatusResponse.SEND_COMMAND_INCORRECT
        return response
    # Pull sender account info
    sender_info = account_info(response["username"])
    if not sender_info:
        response["status"] = StatusResponse.NO_ACCOUNT
        return response
    # Parse the amount
    try:
        response["amount"] = parse_stroop_amount(parsed_text, response["username"])
    except TipError as err:
        response["status"] = StatusResponse.CANNOT_PARSE_AMOUNT
        response["amount"] = parsed_text[1]
        return response
    # Check if it's above the program minimum
    if response["amount"] < to_stroop(PROGRAM_MINIMUM):
        response["status"] = StatusResponse.BELOW_PROGRAM_MINIMUM
        return response
    # Check for sufficient funds
    if response["amount"] > sender_info["balance"]:
        response["status"] = StatusResponse.INSUFFICIENT_FUNDS
        return response
    # Check that it's above the subreddit minimum
    if response["amount"] < to_stroop(response["subreddit_minimum"]):
        response["status"] = StatusResponse.BELOW_SUB_MINIMUM
        return response
    entry_id = add_history_record(
        username = response["username"],
        action = "send",
        comment_or_message = "comment",
        comment_id = message.name,
        reddit_time = message_time,
        comment_text = str(message.body)[:255],
    )
    response["status"] = StatusResponse.SENT_TO_EXISTING_USER
    response["recipient"] = str(message.parent().author)
    recipient_info = account_info(response["recipient"])
    if not recipient_info:
        response["status"] = StatusResponse.SENT_TO_NEW_USER
        recipient_info = add_new_account(response["recipient"])
    elif not recipient_info["opt_in"]:
        response["status"] = StatusResponse.USER_OPTED_OUT
        return response
    # Check if sent to oneself
    if sender_info["username"] == recipient_info["username"]:
        response["status"] = StatusResponse.CANNOT_SEND_TO_YOURSELF
        return response
    LOGGER.info(f"Tipping Cannacoin: {sender_info['username']} {recipient_info['username']} {response['amount']}")
    account_tip(sender_info["username"], recipient_info['username'], response["amount"])
    # Update the sql and send the PMs
    History.update(
        notes = "sent to user",
        recipient_username = recipient_info["username"],
        amount = str(response["amount"]),
        return_status = "cleared"
    ).where(History.id == entry_id).execute()

    if response["status"] == StatusResponse.SENT_TO_NEW_USER:
        subject = SUBJECTS["first_tip"]
        message_text = (WELCOME_TIP % (NumberUtil.format_float(from_stroop(response["amount"])), ACCOUNT, sender_info["memo"]) + COMMENT_FOOTER)
        send_pm(recipient_info["username"], subject, message_text)
        return response
    else:
        if not recipient_info["silence"]:
            recipient_info = account_info(response["recipient"])  # Update balance
            subject = SUBJECTS["new_tip"]
            message_text = (
                NEW_TIP % (NumberUtil.format_float(from_stroop(response["amount"])), 
                from_stroop(recipient_info['balance']))
            ) + COMMENT_FOOTER
            send_pm(recipient_info["username"], subject, message_text)
        return response
