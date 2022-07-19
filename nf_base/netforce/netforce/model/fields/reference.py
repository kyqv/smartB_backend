# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from .field import Field


class Reference(Field):

    def __init__(self, selection, string, **kw):
        super().__init__(string=string, **kw)
        self.selection = selection

    def get_col_type(self):
        return "varchar(64)"

    def get_meta(self, context={}):
        vals = super().get_meta(context=context)
        vals["type"] = "reference"
        vals["selection"] = self.selection
        return vals
