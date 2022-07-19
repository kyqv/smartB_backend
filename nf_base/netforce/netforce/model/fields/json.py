# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from .field import Field


class Json(Field):

    def __init__(self, string, **kw):
        super(Json, self).__init__(string, **kw)

    def get_col_type(self):
        return "text"

    def get_meta(self, context={}):
        vals = super(Json, self).get_meta(context=context)
        vals["type"] = "json"
        return vals
