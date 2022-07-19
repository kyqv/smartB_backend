# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from .field import Field
from netforce.locale import _
import netforce.model


class Selection(Field):

    def __init__(self, selection, string, **kw):
        super(Selection, self).__init__(string=string, **kw)
        self.selection = selection
        if not self.function:
            self.eager_load = True

    def get_col_type(self):
        return "varchar(64)"

    def get_meta(self, context={}):
        vals = super(Selection, self).get_meta(context=context)
        vals["type"] = "selection"
        if isinstance(self.selection, str):
            m = netforce.model.get_model(self.model)
            f = getattr(m, self.selection)
            sel = f(context=context)
        else:
            sel = self.selection
        vals["selection"] = [(k, _(v)) for k, v in sel]
        return vals
