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

from netforce.controller import WebSocketHandler
from multiprocessing import Process
import tornado.ioloop
import time
from netforce.database import get_connection,set_active_db
from netforce.access import get_active_user
from netforce.model import get_model
import os
from netforce import config

POLL_WAIT=2.0
listen_handlers={}
sending_notifs=False

def send_notifs():
    print("send_notifs",os.getpid(),list(listen_handlers.keys()))
    t=time.strftime("%Y-%m-%d %H:%M:%S")
    db_handlers={}
    for listener_id,h in listen_handlers.items(): # XXX
        db_handlers.setdefault(h.dbname,[]).append(listener_id)
    for dbname,listener_ids in db_handlers.items():
        set_active_db(dbname)
        db=get_connection()
        ids_sql="("+",".join(str(x) for x in listener_ids)+")"
        res=db.query("SELECT listener_id,name FROM ws_event WHERE listener_id IN "+ids_sql)
        if res:
            for r in res:
                print("NOTIFY %s %s %s"%(dbname,r.listener_id,r.name))
                handler=listen_handlers[r.listener_id]
                handler.write_message("NOTIFY %s"%r.name)
            db.execute("DELETE FROM ws_event WHERE listener_id IN "+ids_sql)
        db.execute("UPDATE ws_listener SET last_check_time=%s WHERE id IN "+ids_sql,t) # XXX: do this less often
        db.execute("DELETE FROM ws_listener WHERE last_check_time<TIMESTAMP %s-INTERVAL '10 seconds'",t) # XXX: do this less often, FIXME
        db.commit()
    io_loop=tornado.ioloop.IOLoop.instance()
    io_loop.add_timeout(time.time()+POLL_WAIT,send_notifs)

class Listen(WebSocketHandler):
    _path="/listen"

    def open(self):
        print("Listen.open",os.getpid())
        global sending_notifs
        t=time.strftime("%Y-%m-%d %H:%M:%S")
        dbname=config.get("database")
        if not dbname:
            dbname=self.get_cookie("dbname",None)
        if not dbname:
            raise Exception("Can't open websocket, missing dbname")
        set_active_db(dbname)
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

    def on_message(self,message):
        print("Listen.on_message",os.getpid(),self.listener_id,message)

    def on_close(self):
        print("Listen.on_close",os.getpid(),self.listener_id)
        del listen_handlers[self.listener_id]

Listen.register()
