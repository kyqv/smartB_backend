# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

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
