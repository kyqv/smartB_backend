# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from .field import Field


class Boolean(Field):

    def __init__(self, string, **kw):
        super().__init__(string=string, **kw)
        if not self.function:
            self.eager_load = True

    def get_col_type(self):
        return "bool"

    def get_meta(self, context={}):
        vals = super(Boolean, self).get_meta(context=context)
        vals["type"] = "boolean"
        return vals

    def validate(self, val):
        if val:
            return True
        return False
