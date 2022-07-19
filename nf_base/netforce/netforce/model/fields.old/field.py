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

from netforce import database
import netforce.model
from netforce.locale import _


class Field(object):

    def __init__(self, string=None, required=None, function=None, function_multi=False, function_context=None, function_order=None, store=None, on_change=None, on_write=None, translate=False, readonly=False, function_search=None, search=False, index=False, multi_company=False, agg_function=None, sql_function=None, function_write=None):
        self.name = None
        self.model = None
        self.string = string
        self.required = required
        self.function = function
        self.agg_function = agg_function
        self.sql_function = sql_function
        if store is None:
            self.store = function is None and agg_function is None and sql_function is None
        else:
            self.store = store
        self.function_multi = function_multi
        self.eager_load = False
        self.on_change = on_change
        self.on_write = on_write
        self.function_context = function_context or {}
        self.function_order = function_order or 10
        self.translate = translate
        self.function_write = function_write
        if self.function and not self.function_write:
            self.readonly = True
        else:
            self.readonly = readonly
        self.function_search = function_search
        self.search = search
        self.index = index
        self.multi_company = multi_company

    def register(self, model, name):
        self.model = model
        self.name = name

    def update_db(self):
        if self.name == "id":
            return
        m = netforce.model.get_model(self.model)
        if not m._table or not self.store:
            return
        db = database.get_connection()
        col_type = self.get_col_type()
        res = db.get(
            "SELECT * FROM pg_attribute a,pg_type t WHERE attrelid=(SELECT pg_class.oid FROM pg_class JOIN pg_catalog.pg_namespace n ON n.oid=pg_class.relnamespace WHERE relname=%s) AND attname=%s and t.oid=a.atttypid", m._table, self.name)
        if not res:
            print("adding column %s.%s" % (m._table, self.name))
            q = "ALTER TABLE %s ADD COLUMN \"%s\" %s" % (m._table, self.name, col_type)
            db.execute(q)
        else:
            old_col_type = res.typname
            if res.typname == "varchar":
                old_col_type += "(%s)" % (res.atttypmod - 4)
            elif res.typname == "numeric":
                prec = ((res.atttypmod - 4) >> 16) & 0xffff
                scale = (res.atttypmod - 4) & 0xffff
                old_col_type += "(%s,%s)" % (prec, scale)
            if old_col_type != col_type:
                try:
                    print("  changing column %s.%s" % (self.model, self.name))
                    print("    %s -> %s" % (old_col_type, col_type))
                    q = "ALTER TABLE %s ALTER COLUMN \"%s\" TYPE %s" % (m._table, self.name, col_type)
                    if col_type=="int4": # XXX
                        q+=" USING \"%s\"::integer"%self.name
                    db.execute(q)
                except:
                    raise Exception("Failed to update database column type for field '%s' of '%s'" %
                                    (self.name, m._name))
        if self.required and (not res or not res.attnotnull):
            print("  adding not-null for %s.%s" % (self.model, self.name))
            q = "SELECT COUNT(*) AS count FROM %s WHERE \"%s\" IS NULL" % (m._table, self.name)
            res = db.get(q)
            if res.count > 0:
                print("WARNING: can not add not-null constraint for %s.%s" % (self.model, self.name))
            else:
                q = "ALTER TABLE %s ALTER COLUMN \"%s\" SET NOT NULL" % (m._table, self.name)
                db.execute(q)
        elif not self.required and res and res.attnotnull:
            print("  dropping not-null")
            q = "ALTER TABLE %s ALTER COLUMN \"%s\" DROP NOT NULL" % (m._table, self.name)
            db.execute(q)
        if self.index:
            idx_name = m._table + "_" + self.name + "_idx"
            res = db.get("SELECT * FROM pg_index i,pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE c.oid=i.indexrelid AND c.relname=%s", idx_name)
            if not res:
                print("creating index %s" % idx_name)
                db.execute("CREATE INDEX " + idx_name + " ON " + m._table + " (" + self.name + ")")

    def get_meta(self, context={}):
        vals = {
            "name": self.name,
            "string": _(self.string),
            "required": self.required,
            "on_change": self.on_change,
            "readonly": self.readonly,
        }
        return vals

    def validate(self, val):
        if self.required and val is None:
            raise Exception("Field %s is required" % self.name)
        return val
