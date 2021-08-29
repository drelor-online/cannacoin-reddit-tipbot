from time import sleep
from shared import REDDIT, LOGGER, Message, should_stop

LOGGER.info("Starting messenger")
while True:
    if should_stop():
        exit(0)
    results = Message.select()
    for result in results:
        LOGGER.info("%s %s %s" % (result.username, result.subject, repr(result.body)[:50]))
        try:
            REDDIT.redditor(str(result.username)).message(str(result.subject), str(result.body))
        except:
            pass
        Message.delete().where(Message.id == result.id).execute()   
    sleep(6)
