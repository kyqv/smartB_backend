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
from datetime import *
import time


def get_days(n):
    days = []
    d = date.today()
    days.append(d.strftime("%Y-%m-%d"))
    while n > 1:
        d -= timedelta(days=1)
        days.append(d.strftime("%Y-%m-%d"))
        n -= 1
    days.reverse()
    return days


def js_time(d):
    return time.mktime(datetime.strptime(d, "%Y-%m-%d").timetuple()) * 1000


class Workcenter(Model):
    _name = "workcenter"
    _string = "Workcenter"
    _key = ["code"]
    _export_name_field = "code"
    _fields = {
        "code": fields.Char("Workcenter Code", search=True),
        "name": fields.Char("Workcenter Name", search=True),
        "location_id": fields.Many2One("stock.location", "Location"),
        "asset_id": fields.Many2One("account.fixed.asset", "Fixed Asset"),
        "hours_history": fields.Json("Hours History", function="get_hours_history"),
        "hours_week": fields.Decimal("Hours This Week", function="get_hours", function_multi=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "documents": fields.One2Many("document", "related_id", "Documents"),
    }
    _order = "code"

    def name_get(self, ids, context={}):
        vals = []
        for obj in self.browse(ids):
            if obj.code:
                name = "%s [%s]" % (obj.name, obj.code)
            else:
                name = obj.name
            vals.append((obj.id, name))
        return vals

    def name_search(self, name, condition=None, context={}, limit=None, **kw):
        cond = [["code", "ilike", "%" + name + "%"]]
        if condition:
            cond = [cond, condition]
        ids1 = self.search(cond, limit=limit)
        cond = [["name", "ilike", "%" + name + "%"]]
        if condition:
            cond = [cond, condition]
        ids2 = self.search(cond, limit=limit)
        ids = list(set(ids1 + ids2))
        return self.name_get(ids, context=context)

    def get_hours_history(self, ids, context={}):
        db = get_connection()
        vals = {}
        days = get_days(30)
        for id in ids:
            res = db.query(
                "SELECT o.date,SUM(o.hours) AS hours FROM mrp_operation o WHERE workcenter_id=%s GROUP BY o.date", id)
            hours = {}
            for r in res:
                hours[r.date] = r.hours
            data = []
            for d in days:
                data.append((js_time(d), hours.get(d, 0)))
            vals[id] = data
        return vals

    def get_hours(self, ids, context={}):
        db = get_connection()
        d = date.today()
        date_from = d - timedelta(days=d.weekday())
        vals = {}
        for id in ids:
            res = db.get(
                "SELECT SUM(o.hours) AS hours FROM mrp_operation o WHERE o.workcenter_id=%s AND o.date>=%s", id, date_from)
            vals[id] = {
                "hours_week": res.hours or 0,
            }
        return vals

Workcenter.register()
