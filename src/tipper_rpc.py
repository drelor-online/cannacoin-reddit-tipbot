from datetime import datetime
from stellar_sdk import Server, Account, Keypair, Network, TransactionBuilder, Asset
from stellar_sdk.exceptions import SdkError

from shared import (
    DEFAULT_URL,
    DEFAULT_FEE,
    CURRENCY,
    CURRENCY_ISSUER,
    ACCOUNT,
    SECRET,
    LOGGER,
    to_stroop,
    from_stroop
)

server = Server(horizon_url=DEFAULT_URL)

# Get a workable fee to prevent a transaction from getting stuck.
def get_fee():
    try:
        fee_stats = server.fee_stats().call()
        base_fee = int(fee_stats["last_ledger_base_fee"])
        ledger_capacity_usage = float(str(fee_stats["ledger_capacity_usage"]))
        higher_fee = int(fee_stats["fee_charged"]["p70"])        
        if (ledger_capacity_usage >= 0.9): # Ledger almost fully used
            return higher_fee 
        else:
            return base_fee
    except SdkError:
        return DEFAULT_FEE 

# Check if an account is open.
def is_account_open(account):
    try:
        accounts = server.accounts().account_id(account).call()
        return True
    except SdkError:
        pass
    return False

# Check if an account is open.
def account_has_trustline(account, asset_name, asset_issuer):    
    try:
        asset = Asset(asset_name, asset_issuer)
        accounts = server.accounts().account_id(account).for_asset(asset).call()
        return True
    except SdkError:
        pass
    return False

# Get balances of XLM and assets in the main account.
def get_balances(account):
    balances = {}
    try:
        accounts = server.accounts().account_id(account).call()
        for balance in accounts["balances"]:
            if balance["asset_type"] == "native":
                balances["xlm"] = to_stroop(balance["balance"])    
            else:
                balances[balance["asset_code"].lower()] = to_stroop(balance["balance"])
    except SdkError:
        LOGGER.exception("Cannot get balances")
    return balances


# Check if a transaction is successful.
def is_transaction_successful(transaction_hash):
    try:
        payments = server.payments().for_transaction(transaction_hash).call()        
        transaction_successful = True
        for payment in payments["_embedded"]["records"]:
            transaction_successful &= payment["transaction_successful"]
        return transaction_successful
    except SdkError:
        LOGGER.exception("Cannot get transaction state for %s" % transaction_hash)
    return False


# Get transaction amount.
def get_transaction_payments(transaction_hash):
    payments = []
    try:
        payments_call_result = server.payments().for_transaction(transaction_hash).call()        
        # Assume only one payment per transaction.
        for payment in payments_call_result["_embedded"]["records"]:
            if "asset_code" in payment:
                asset = payment["asset_code"].lower()
            else:
                asset = "xlm"
            if not "amount" in payment:
                continue
            payments.append({"from": payment["from"], "to": payment["to"], "asset": asset, "amount": to_stroop(str(payment["amount"]))})
    except SdkError:
        LOGGER.exception("Cannot get transaction state for %s" % transaction_hash)
    return payments


# Get the most recent incoming transactions.
def get_incoming_transactions():
    transactions = []
    try:
        transactions_call_result = server.transactions().for_account(account_id=ACCOUNT).include_failed(False).order(desc=True).limit(200).call()
        for transaction in transactions_call_result["_embedded"]["records"]:
            if transaction["source_account"] == ACCOUNT: 
                continue
            date = datetime.strptime(transaction["created_at"][:19], "%Y-%m-%dT%H:%M:%S")
            transactions.append({"hash" : transaction["hash"], "date" : date, "source_account": transaction["source_account"], "memo": transaction.get('memo', None)})
    except SdkError:
        LOGGER.exception("Cannot get incoming transactions")
    return transactions


def get_sequence_number():
    try:
        account = server.accounts().account_id(ACCOUNT).call()
        return int(account['sequence'])       
    except SdkError:
        LOGGER.exception("Cannot get sequence number")


def send_payment(destination_account, amount, memo, fee):
# Send a payment to an account.
    try:
        source_keypair = Keypair.from_secret(SECRET)
        source_account = server.load_account(source_keypair.public_key)
        #root_account = Account(account_id = source_keypair.public_key, sequence=1)
        transaction = (
            TransactionBuilder(
                source_account = source_account,
                network_passphrase = Network.PUBLIC_NETWORK_PASSPHRASE,
                base_fee = fee,
            )
            .add_text_memo(memo)
            .append_payment_op(
                destination = destination_account,
                amount = str(from_stroop(amount)),
                #asset_code = CURRENCY,
                #asset_issuer = CURRENCY_ISSUER
                asset = Asset(CURRENCY, CURRENCY_ISSUER)
            )
            .set_timeout(20)
            .build()
        )
        transaction.sign(source_keypair)
        response = server.submit_transaction(transaction)
        return response["successful"]
    except SdkError:
        LOGGER.exception("Cannot send transaction")
    return False    
