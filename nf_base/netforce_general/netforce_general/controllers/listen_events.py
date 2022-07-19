from netforce.controller import WebSocketHandler
from netforce import ipc
import json
import tornado.ioloop
import datetime
import os

_handlers=[]

def _send_event():
    pid = os.getpid()
    print("send_event pid=%s" % pid)
    print("%d handlers"%len(_handlers))
    for h in _handlers:
        data={
            "event": "new_message", # XXX
        }
        msg=json.dumps(data)
        h.write_message(msg)

ipc.set_signal_handler("new_event", _send_event)

class ListenEvents(WebSocketHandler):
    _path="/listen_events"

    def check_origin(self,origin):
        return True

    def open(self):
        print("ListenEvents.open")
        _handlers.append(self)

    def on_close(self):
        print("ListenEvents.on_close")
        i=_handlers.index(self)
        del _handlers[i]

ListenEvents.register()
