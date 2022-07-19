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

from netforce.model import Model, fields, get_model
import time
from netforce.access import get_active_user, get_ip_addr, set_active_user
from netforce.utils import get_ip_country
from netforce import database
from netforce import logger
import json
from datetime import *
import time

class Log(Model):
    _name = "log"
    _string = "Log Entry"
    _fields = {
        "date": fields.DateTime("Date", required=True, search=True),
        "user_id": fields.Many2One("base.user", "User", search=True),
        "ip_addr": fields.Char("IP Address", search=True),
        "country_id": fields.Many2One("country", "Country", readonly=True),
        "message": fields.Text("Message", required=True, search=True),
        "details": fields.Text("Details", search=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "related_id": fields.Reference([],"Related To"),
        "txid": fields.Char("Transaction ID",search=True),
        "fields_changed": fields.Text("Fields Changed",function="get_fields_changed"),
        "entry_point": fields.Char("Entry Point",search=True),
        "type": fields.Selection([["info","Info"],["warning","Warning"],["error","Error"]],"Type",search=True,index=True),
        "client_name": fields.Char("Client Name",index=True,search=True),
    }
    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _order = "id desc"

    def log(self, msg, details=None, ip_addr=None, related_id=None, type=None):
        uid = get_active_user()
        if not ip_addr:
            ip_addr = get_ip_addr()
        try:
            country_code = get_ip_country(ip_addr)
            res = get_model("country").search([["code", "=", country_code]])
            country_id = res[0]
        except Exception as e:
            #print("Failed to get IP country: %s"%e)
            country_id = None
        db=database.get_connection()
        res=db.get("SELECT txid_current() AS txid")
        txid=res.txid if res else None
        entry_point=logger.get_entry_point()
        client_name=logger.get_client_name()
        vals = {
            "user_id": uid,
            "ip_addr": ip_addr,
            "message": msg,
            "details": details,
            "country_id": country_id,
            "related_id": related_id,
            "txid": txid,
            "entry_point": entry_point,
            "client_name": client_name,
            "type": type or "info",
        }
        set_active_user(1)
        self.create(vals)
        set_active_user(uid)

    def get_fields_changed(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            try:
                data=json.loads(obj.details)
                fnames=[]
                for n in data:
                    if n in ("write_time","create_time","write_uid","create_uid"):
                        continue
                    fnames.append(n)
                fnames.sort()
                vals[obj.id]=", ".join(fnames)
            except:
                vals[obj.id]=None
        return vals

    def recover_test(self,ids,context={}):
        obj=self.browse(ids[0])
        data=json.loads(obj.details)
        body=data["body"]
        get_model("cms.page").write([97],{"body":body})

    def test_slow(self,context={}):
        time.sleep(10)

    def get_errors_per_day(self,context={}):
        db=database.get_connection()
        from_t=(datetime.now()-timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        res=db.query("SELECT date_trunc('day',date) AS day,COUNT(*) AS num_warnings FROM log WHERE date>=%s AND type='warning' AND client_name IS NOT NULL GROUP BY day ORDER BY day",from_t);
        data1=[]
        for r in res:
            d=datetime.strptime(r.day[:10],"%Y-%m-%d")
            data1.append([time.mktime(d.timetuple()) * 1000, r.num_warnings])
        res=db.query("SELECT date_trunc('day',date) AS day,COUNT(*) AS num_errors FROM log WHERE date>=%s AND type='error' AND client_name IS NOT NULL GROUP BY day ORDER BY day",from_t);
        data2=[]
        for r in res:
            d=datetime.strptime(r.day[:10],"%Y-%m-%d")
            data2.append([time.mktime(d.timetuple()) * 1000, r.num_errors])
        return [
            {
                "name": "Warnings",
                "data": data1,
            },
            {
                "name": "Errors",
                "data": data2,
            },
        ]

Log.register()
