# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from .field import Field


class Binary(Field):

    def __init__(self, string, required=False):
        super(Binary, self).__init__(string=string, required=required)

    def get_col_type(self):
        return "varchar(64)"

    def get_meta(self, context={}):
        vals = super(Binary, self).get_meta(context=context)
        vals["type"] = "binary"
        return vals
