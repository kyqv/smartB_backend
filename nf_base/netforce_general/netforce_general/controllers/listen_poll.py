# Copyright (c) 2012-2015 Netforce Co. Ltd.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

from netforce.controller import Controller
import tornado.ioloop
import tornado.web
import time
from netforce.database import get_connection,set_active_db,get_active_db
from netforce.access import get_active_user
from netforce.model import get_model
import os
from netforce import config
import json

POLL_WAIT=2.0
listen_handlers={}
sending_notifs=False

def send_notifs():
    #print("send_notifs",os.getpid(),list(listen_handlers.keys()))
    t=time.strftime("%Y-%m-%d %H:%M:%S")
    db_handlers={}
    for listener_id,h in listen_handlers.items(): # XXX
        db_handlers.setdefault(h.dbname,[]).append(listener_id)
    for dbname,listener_ids in db_handlers.items():
        set_active_db(dbname)
        db=get_connection()
        try:
            ids_sql="("+",".join(str(x) for x in listener_ids)+")"
            res=db.query("SELECT listener_id,name FROM ws_event WHERE listener_id IN "+ids_sql)
            if res:
                handler_events={}
                for r in res:
                    handler_events.setdefault(r.listener_id,[]).append(r.name)
                for listener_id,events in handler_events.items():
                    print("NOTIFY %s %s %s"%(dbname,listener_id,events))
                    handler=listen_handlers[listener_id]
                    handler.write(json.dumps(events))
                    handler.finish()
                    del listen_handlers[listener_id]
                db.execute("DELETE FROM ws_event WHERE listener_id IN "+ids_sql)
            db.execute("UPDATE ws_listener SET last_check_time=%s WHERE id IN "+ids_sql,t) # XXX: do this less often
            db.execute("DELETE FROM ws_listener WHERE last_check_time<TIMESTAMP %s-INTERVAL '10 seconds'",t) # XXX: do this less often, FIXME
            db.commit()
        except:
            print("#########################################################")
            print("ERROR: send_notifs failed")
            db.rollback()
            import traceback
            traceback.print_exc()
    io_loop=tornado.ioloop.IOLoop.instance()
    io_loop.add_timeout(time.time()+POLL_WAIT,send_notifs)

class ListenPoll(Controller):
    _path="/listen_poll"

    @tornado.web.asynchronous
    def get(self):
        raise Exception("Polling is disabled") # XXX
        #print("ListenPoll.get",os.getpid())
        global sending_notifs
        t=time.strftime("%Y-%m-%d %H:%M:%S")
        dbname=get_active_db()
        if not dbname:
            raise Exception("Missing dbname in long poll request")
        db=None
        try:
            db=get_connection()
            user_id=self.get_cookie("user_id",None)
            if user_id:
                user_id=int(user_id)
            res=db.get("INSERT INTO ws_listener (user_id,last_check_time) VALUES (%s,%s) RETURNING id",user_id,t)
            self.listener_id=res.id
            self.dbname=dbname
            listen_handlers[self.listener_id]=self
            if not sending_notifs:
                io_loop=tornado.ioloop.IOLoop.instance()
                io_loop.add_timeout(time.time()+POLL_WAIT,send_notifs) # XXX: should start this directly when process is started?
                sending_notifs=True
            db.commit()
        except:
            print("#########################################################")
            print("ERROR: ListenPoll.get failed")
            if db:
                db.rollback()
            import traceback
            traceback.print_exc()

    def on_connection_close(self):
        #print("ListenPoll.on_connection_close",os.getpid(),self.listener_id)
        del listen_handlers[self.listener_id]

ListenPoll.register()
