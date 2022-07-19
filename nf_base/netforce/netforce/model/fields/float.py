# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from .field import Field


class Float(Field):

    def __init__(self, string, **kw):
        super(Float, self).__init__(string=string, **kw)
        if not self.function:
            self.eager_load = True

    def get_col_type(self):
        return "double precision"

    def get_meta(self, context={}):
        vals = super(Float, self).get_meta(context=context)
        vals["type"] = "float"
        return vals

    def validate(self, val):
        super(Float, self).validate(val)
        if val is None:
            return None
        return float(val)
