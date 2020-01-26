from lib import *

## LIST APPNAME ##
#android = android
#ios = ios
#android lite = android_lite
#chrome os = chrome
#iosipad = ios_ipad

##LOGIN QR##
client = Boteater(my_app='ios_ipad') ## Change server to jp if use japan vps
clientMid= client.profile.mid
##LOGIN TOKEN##
#client = Boteater(my_token="", my_app='ios_ipad') ## Change server to jp if use japan vps

def MyWorker(op):
    if op.type in [25, 26]:
        msg = op.message
        text = str(msg.text)
        msg_id = msg.id
        receiver = msg.to
        msg.from_ = msg._from
        sender = msg._from
        cmd = text.lower()
        if msg.toType == 0 and sender != clientMid: to = sender
        else: to = receiver

        if cmd == "hallo":
            client.sendMessageReply(to, "hai", msg.id)

def run():
    while True:
        try:
            ops = client.fetchOperation()
            for op in ops:
                if op.revision > client.lastOP:
                    client.lastOP = max(op.revision, client.lastOP)
                    MyWorker(op)
                    ## Jangan threading disini :) ##
                    ## Don't threading in here :) ##
        except Exception as e:
            print(e)

if __name__ == "__main__":
    run()
        
