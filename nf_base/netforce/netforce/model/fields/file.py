# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from .field import Field


class File(Field):

    def __init__(self, string, **kw):
        super(File, self).__init__(string=string, **kw)

    def get_col_type(self):
        return "varchar(256)"

    def get_meta(self, context={}):
        vals = super(File, self).get_meta()
        vals["type"] = "file"
        return vals
