# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from .field import Field


class One2Many(Field):

    def __init__(self, relation, relfield, string, condition=None, operator=None, order=None, **kw):
        super(One2Many, self).__init__(string=string, **kw)
        self.relation = relation
        self.relfield = relfield
        self.store = False
        self.condition = condition
        self.operator = operator
        self.order = order

    def get_meta(self, context={}):
        vals = super(One2Many, self).get_meta(context=context)
        vals["type"] = "one2many"
        vals["relation"] = self.relation
        return vals
