# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from .field import Field


class Integer(Field):

    def __init__(self, string, **kw):
        super(Integer, self).__init__(string=string, **kw)
        if not self.function:
            self.eager_load = True

    def get_col_type(self):
        return "int4"

    def get_meta(self, context={}):
        vals = super(Integer, self).get_meta(context=context)
        vals["type"] = "integer"
        return vals

    def validate(self, val):
        super(Integer, self).validate(val)
        if val is None:
            return None
        return int(val)
