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


class Many2One(Field):

    def __init__(self, relation, string, condition=None, on_delete=None, **kw):
        super(Many2One, self).__init__(string=string, index=True, **kw)
        self.on_delete = on_delete or "set_null"
        self.relation = relation
        self.condition = condition
        if self.store:
            self.eager_load = True

    def update_db(self):
        super(Many2One, self).update_db()
        m = netforce.model.get_model(self.model)
        if not m._table or not self.store:
            return
        db = database.get_connection()
        fkname = m._table + "_" + self.name + "_fk"
        if self.on_delete == "restrict":
            delete_rule = "r"
            on_delete_sql = "RESTRICT"
        elif self.on_delete == "no_action":
            delete_rule = "a"
            on_delete_sql = "NO_ACTION"
        elif self.on_delete == "cascade":
            delete_rule = "c"
            on_delete_sql = "CASCADE"
        elif self.on_delete == "set_null":
            delete_rule = "n"
            on_delete_sql = "SET NULL"
        elif self.on_delete == "set_default":
            delete_rule = "d"
            on_delete_sql = "SET DEFAULT"
        else:
            raise Exception("Invalid on_delete on %s.%s (%s)" % (m._name, self.name, self.on_delete))
        mr = netforce.model.get_model(self.relation)
        if not mr:
            raise Exception("Relation model '%s' does not exist" % self.relation)
        drop_fk = False
        add_fk = False
        res = db.get(
            "SELECT r.relname,c.confdeltype FROM pg_constraint c,pg_class r JOIN pg_catalog.pg_namespace n ON n.oid=r.relnamespace WHERE c.conname=%s AND r.oid=c.confrelid", fkname)
        if not res:
            print("adding foreign key %s.%s" % (self.model, self.name))
            drop_fk = False
            add_fk = True
        else:
            if res.confdeltype != delete_rule or res.relname != mr._table:
                print("changing foreign key %s.%s" % (self.model, self.name))
                print("  delete_rule: %s -> %s" % (res.confdeltype, delete_rule))
                print("  relation: %s -> %s" % (res.relname, mr._table))
                drop_fk = True
                add_fk = True
        if drop_fk:
            db.execute("ALTER TABLE %s DROP CONSTRAINT %s" % (m._table, fkname))
        if add_fk:
            q = "ALTER TABLE %s ADD CONSTRAINT %s FOREIGN KEY (%s) REFERENCES %s (id)" % (
                m._table, fkname, self.name, mr._table)
            if self.on_delete:
                q += " ON DELETE %s" % on_delete_sql
            print(q)
            db.execute(q)

    def get_col_type(self):
        return "int4"

    def get_meta(self, context={}):
        vals = super(Many2One, self).get_meta(context=context)
        vals["type"] = "many2one"
        vals["relation"] = self.relation
        return vals
