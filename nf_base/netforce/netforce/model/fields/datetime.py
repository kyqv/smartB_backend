# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from .field import Field


class DateTime(Field):

    def __init__(self, string, **kw):
        super(DateTime, self).__init__(string=string, **kw)
        if not self.function:
            self.eager_load = True

    def get_col_type(self):
        return "timestamp"

    def get_meta(self, context={}):
        vals = super(DateTime, self).get_meta(context=context)
        vals["type"] = "datetime"
        return vals
