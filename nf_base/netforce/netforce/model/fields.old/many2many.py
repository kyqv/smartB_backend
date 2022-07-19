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

from .field import Field
from netforce import database
import netforce.model


class Many2Many(Field):

    def __init__(self, relation, string, reltable=None, relfield=None, relfield_other=None, condition=None, **kw):
        super(Many2Many, self).__init__(string=string, **kw)
        self.relation = relation
        self.reltable = reltable
        self.relfield = relfield
        self.relfield_other = relfield_other
        self.store = False
        self.condition = condition

    def register(self, model, name):
        super(Many2Many, self).register(model, name)
        table = self.model.replace(".", "_")  # XXX: to fix register order problem
        rtable = self.relation.replace(".", "_")
        if not self.reltable:
            table1 = min(table, rtable)
            table2 = max(table, rtable)
            self.reltable = "m2m_" + table1 + "_" + table2
        if not self.relfield:
            self.relfield = table + "_id"
        if not self.relfield_other:
            self.relfield_other = rtable + "_id"

    def get_meta(self, context={}):
        vals = super(Many2Many, self).get_meta(context=context)
        vals["type"] = "many2many"
        vals["relation"] = self.relation
        return vals

    def update_db(self):
        m = netforce.model.get_model(self.model)
        mr = netforce.model.get_model(self.relation)
        db = database.get_connection()
        res = db.get("SELECT * FROM pg_class JOIN pg_catalog.pg_namespace n ON n.oid=pg_class.relnamespace WHERE relname=%s", self.reltable)
        if not res:
            db.execute("CREATE TABLE %s (%s int4 NOT NULL REFERENCES %s(id) ON DELETE CASCADE, %s int4 NOT NULL REFERENCES %s(id) ON DELETE CASCADE)" % (
                self.reltable, self.relfield, m._table, self.relfield_other, mr._table))

    def validate(self, val):
        super(Many2Many, self).validate(val)
        if val is None:
            return None
        return [int(id) for id in val.split(",")]
