# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from .field import Field


class Array(Field):

    def __init__(self, string, **kw):
        super(Array, self).__init__(string=string, **kw)

    def get_col_type(self):
        return "integer[]"

    def get_meta(self, context={}):
        vals = super(Array, self).get_meta(context=context)
        vals["type"] = "integer[]"
        return vals
