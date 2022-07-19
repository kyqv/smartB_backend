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
import time
from netforce.database import get_connection
from netforce import utils


class FieldCache(Model):
    _name = "field.cache"
    _string = "Field Cache"
    _fields = {
        "model": fields.Char("Model", index=True),
        "field": fields.Char("Field", index=True),
        "record_id": fields.Integer("Record ID", index=True),
        "value": fields.Text("Value"),
        "ctime": fields.DateTime("Time Created"),
    }
    _indexes = [
        ("model", "field", "record_id"),
    ]

    def get_value(self, model, field, ids, min_ctime=None):
        db = get_connection()
        q = "SELECT record_id,value,ctime FROM field_cache WHERE model=%s AND field=%s AND record_id IN %s"
        args = [model, field, tuple(ids)]
        if min_ctime:
            q += " AND ctime>=%s"
            args.append(min_ctime)
        res = db.query(q, *args)
        vals = {}
        for r in res:
            vals[r.record_id] = utils.json_loads(r.value)
        return vals

    def set_value(self, model, field, record_id, value):
        ctime = time.strftime("%Y-%m-%d %H:%M:%S")
        db = get_connection()
        db.execute("DELETE FROM field_cache WHERE model=%s AND field=%s AND record_id=%s", model, field, record_id)
        db.execute("INSERT INTO field_cache (model,field,record_id,value,ctime) VALUES (%s,%s,%s,%s,%s)",
                   model, field, record_id, utils.json_dumps(value), ctime)

    def clear_cache(self, model):
        db = get_connection()
        db.execute("DELETE FROM field_cache WHERE model=%s", model)

FieldCache.register()
