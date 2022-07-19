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

from netforce.model import Model, fields
from netforce.database import get_connection
import time


class WSEvent(Model):
    _name = "ws.event"
    _log_access = False
    _fields = {
        "listener_id": fields.Many2One("ws.listener", "Listener", on_delete="cascade"),
        "name": fields.Char("Name", required=True),
        "ctime": fields.DateTime("Create Time", required=True),
    }

    def new_event(self, event_name, user_id):
        print("WSEvent.new_event", event_name, user_id)
        t = time.strftime("%Y-%m-%d %H:%M:%S")
        db = get_connection()
        if user_id:
            res = db.query("SELECT id FROM ws_listener WHERE user_id=%s", user_id)
        else:
            res = db.query("SELECT id FROM ws_listener")
        for r in res:
            db.execute("INSERT INTO ws_event (listener_id,name,ctime) VALUES (%s,%s,%s)", r.id, event_name, t)

WSEvent.register()
