# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from .field import Field


class Time(Field):

    def __init__(self, string, required=False):
        super(Time, self).__init__(string=string, required=required)
        if not self.function:
            self.eager_load = True

    def get_col_type(self):
        return "time"

    def get_meta(self, context={}):
        vals = super(Time, self).get_meta(context=context)
        vals["type"] = "time"
        return vals
