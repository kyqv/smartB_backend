# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from .field import Field


class Text(Field):

    def __init__(self, string, **kw):
        super(Text, self).__init__(string=string, **kw)

    def get_col_type(self):
        return "text"

    def get_meta(self, context={}):
        vals = super(Text, self).get_meta(context=context)
        vals["type"] = "text"
        return vals
