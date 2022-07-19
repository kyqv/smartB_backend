# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from .field import Field
from decimal import *


class Decimal(Field):

    def __init__(self, string, precision=16, scale=2, **kw):
        super(Decimal, self).__init__(string=string, **kw)
        self.precision = precision
        self.scale = scale
        if not self.function:
            self.eager_load = True

    def get_col_type(self):
        return "numeric(%d,%d)" % (self.precision, self.scale)

    def get_meta(self, context={}):
        vals = super(Decimal, self).get_meta(context=context)
        vals["type"] = "decimal"
        return vals

    def validate(self, val):
        super(Decimal, self).validate(val)
        if val is None:
            return None
        return Decimal(val)
