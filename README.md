
  

# Poopstar Reddit Tip Bot 

  

...is a reddit tipping service to easily give Poopstar to your favorite Redditors! [Poopstar](https://poopstar.online) is a stinky, filthy but wholesome universal cryptocurrency based on the Stellar network. Before using Poopstar Tipper, please take a look at the [Terms of Service](https://github.com/drelor-online/poopstar-reddit-tipbot#terms-of-service).

  

  

It is a fork and modification of the [Ananos (Stellar) Reddit Tipbot by swartbeens](https://github.com/swartbeens/ananos-stellar-reddit-tipbot) which is a fork and modification of the [Banano](https://banano.cc) reddit tip bot created by /u/bbedward - which is available on [GitHub](https://github.com/BananoCoin/banano_reddit_tipbot).

  

  

### To get started with the Poopstar Tip Bot, either:

  

A) **Create an account** by [sending a message](https://reddit.com/message/compose/?to=poopstar_tipbot&subject=command&message=create) to /u/poopstar_tipbot with 'create' or 'register' in the message body.

  

\-or-

  

B) **Receive a Poopstar tip** from a fellow redditor, and you will automatically have an account made! Be sure to activate it afterwards by [sending a message](https://reddit.com/message/compose/?to=poopstar_tipbot&subject=command&message=create) to /u/poopstar_tipbot.

  

Once you have funds in your account, you can tip other redditors, or send to any Poopstar address via PM to /u/poopstar_tipbot.

  

# Comment Replies:

  

The Poopstar tip bot is intended for tipping small amounts on Reddit posts and replies.

  

  

On supported subreddits, you can send a tip like this:

  

  

`!poop 1 This is great!`

  

  

This will tip a redditor 1 Poopstar. !poop <amount> must be the first thing in your message OR the last thing. Such, this is also a valid tip:

  

  

`This is great! !poop 1`

  

  

Or from anywhere on reddit, you can tip a commenter by mentioning the tip bot:

  

  

`/u/poopstar_tipbot 1`

  
  

  

If the subreddit is a friendly subreddit, the bot will respond with a message. If the subreddit is not friendly, a PM will be sent to both the sender and the recipient.

  

# Private Messages

  

  

The Poopstar tip bot also works by PM. [Send a message](https://reddit.com/message/compose/?to=poopstar_tipbot&subject=command&message=type_command_here) to /u/poopstar_tipbot for a variety of actions.

  

  

To send 1 Poopstar to drelor, include this text in the message body:

  

  

`send 1 drelor`

  
  

  

To send 1 Poopstar to Stellar address G...., include this text in the message body:

  

  

`send 1 G...`

  

  

or send all your balance:

  

  

`send all G...`

  

*Note that the address you are sending to must have a trustline with the Poopstar address on Stellar (GBDJHODFOQHSBZ4B3PTLMDBXTSIQWD6V6RZT5YNOFW5P44LTH6P4QEAL) and you cannot send from an exchange wallet.*

  

There are many other commands.

  

  

```
'balance' or 'address' - Retrieve your account balance.
'create' - Create a new account if one does not exist
'help' - Get this help message 
'history <optional: number of records>' - Retrieves tip bot commands.  
'send <amount or all, optional: Currency> <user/address>' - Send Poopstar to a reddit user or an address  
'silence <yes/no>' - (default 'no') Prevents the bot from sending you tip notifications or tagging in posts  
'subreddit <subreddit> <'activate'/'deactivate'> <option>' - Subreddit Moderator Controls - Enabled Tipping on Your Sub (`silent`, `full`)  
'opt-out' - Disables your account.  
'opt-in' - Re-enables your account.
```

  

### Control tip bot Behavior on your subreddit

  

If you are a moderator of a subreddit, and would like to tipping to your sub, use the `subreddit` command. For example, to activate tipping on the r/ananos subreddit, I send a PM to the bot saying:

  

  

`subreddit ananos activate`

  

  

This will allow the bot to look for !poop commands and respond to posts in that subreddit.

  

-or- If I don't want the bot to respond, but still want tips:

  

  

`subreddit ananos activate silent`

  
  
  
  

  

To deactivate, simply PM

  

  

`subreddit ananos deactivate`

  

  

### Here's a few other great links:


[Poopstar Subreddit](https://reddit.com/r/poopstar) -- Post any questions about Poopstar  
  

[Ananos Subreddit](https://reddit.com/r/ananos) -- Post any questions about Ananos

  

[Banano Subreddit](https://reddit.com/r/banano) -- Post any questions about Banano

  

[Banano Tipper GitHub](https://github.com/BananoCoin/banano_reddit_tipbot) -- This software is open source!

  

[BANANO](https://banano.cc) -- The Official BANANO website

  
  
  

  

# Terms of Service

  

* Do not keep a lot of Poopstar in your tip bot account! The tip bot is for tipping small amounts ONLY.

  

* You accept the risks of using this tip bot -- We won't steal your Poopstar, but they might be lost at any point, and we are at no obligation to replace them. Don't put in more than you're willing to lose.

  

* We are under no obligation to provide support. The tip bot is not a custodial service.

  

* Any consequences of tipping are the responsibility of the users using this service.

  

* This software is provided "as is" and any express or implied warranties, including, but not limited to, the implied warranties of merchantability and fitness for a particular purpose are disclaimed. In no event shall the copyright holder or contributors be liable for any direct, indirect, incidental, special, exemplary, or consequential damages (including, but not limited to, procurement of substitute goods or services; loss of use, data, or profits; or business interruption) however caused and on any theory of liability, whether in contract, strict liability, or tort (including negligence or otherwise) arising in any way out of the use of this software, even if advised of the possibility of such damage.

  

  

# FAQ

  

## Why does the message have to start or end with !poop<amount>?

  

This is to prevent unintentional tips! If the program simply scanned the entire comment, a user might accidentally quote someone else's tip command in a response. In the future I might change this, but for now it's the best way to ensure the program behaves as expected.

  

  

## Are my funds safe?

  

**NO! Unless you and you alone control your private keys, your funds are never safe!** Please don't keep more than a small dose of Poopstar on the tip bot at any time! **Use at your own risk!**

  
  
## What about fees?

  
Unfortunately, Stellar requires fees to send transactions. The tipping happens off-chain to circumvent this. However, the bot needs to pay a small amount of XLM at each withdrawal. 
You can prevent withdrawal problems and support the bot by donating a little XLM to the bot's address: 
GDEU67YJKQSNO4RW3KQBNUZ4AYAQ4V2MPYCFLG254RBTSFOXYRUVH3XZ.

  

## I sent a tip to the wrong address. Can I get it back?

  

If the address isn't affiliated with a Redditor, **No.**

  

  

## I sent a tip to the wrong redditor. Can I get it back?

  

Your best bet is to try to reach out to the redditor and ask for it back. Do not harass other redditors or do anything that would violate Reddit's Terms of Service.

  

  

## I tried to send a tip, but received no response. Did it go through?

  

Probably not. It's most likely the bot was temporarily disconnected. If a command is issued while the bot is offline, the command will not be seen. If no response is received from the bot after a few minutes, send a message to the bot with the text 'history'. If you get a response and the tip isn't in your history, that means it wasn't seen. If you don't get a response, the bot is probably still offline. Try again in a few minutes.

  

  

## I found a bug or I have a concern. Question Mark?

  

Post it on the [Poopstar subreddit](https://reddit.com/r/Poopstar) .

  

  

# Error Codes

  

If a reddit tip is a reply to a reply, it's better to keep a short message with an error code.

  

* 100 - You do not have an account -- Create an account by typing 'create' or by receiving a tip from another redditor.

  

* 110 - You must specify an amount and a user, e.g. `send 1 ananos_tipbot`.

  

* 111 - You have specified too many arguments.

  

* 120 - Could not read the tip amount -- use either a number or the word 'all'.

  

* 130 - Tip amount is below program minimum -- This is to prevent spamming other redditors.

  

* 150 - This subreddit does not accept tips this small, increase your tip or send the bot `subreddit subreddit_name` to see what the minimum is.

  

* 160 - You have insufficient funds.

  

* 170 - The target you specified is neither a redditor or an address.

  

* 190 - The recipient has disabled tipping for their account.

  

* 200 - You have tried to tip your own comment or withdraw to your own account, which is not allowed.

  

* 210 - Failed to send funds to Stellar address. Check that you have a trustline with Poopstar and enough XLM funds.

* 220 - Not enough XLM to perform withdrawal.

* 230 - Withdrawal account has no Poopstar trustline.
