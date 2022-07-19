# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from .field import Field


class Char(Field):

    def __init__(self, string, size=256, password=False, **kw):
        super(Char, self).__init__(string=string, **kw)
        self.size = size
        self.password = password
        if not self.function:
            self.eager_load = True

    def get_col_type(self):
        return "varchar(%d)" % self.size

    def get_meta(self, context={}):
        vals = super(Char, self).get_meta(context=context)
        vals["type"] = "char"
        vals["size"] = self.size
        return vals

    def validate(self, val):
        super(Char, self).validate(val)
        return val
