# Copyright (c) 2012-2015 Netforce Co. Ltd.

from netforce.model import Model, fields
from netforce import utils

class Screen(Model):
    _name = "screen"
    _string = "Screen"
    _fields = {
        "name": fields.Char("Screen Name",required=True),
        "layout": fields.Text("Layout"),
    }
    _order="name"

Screen.register()
