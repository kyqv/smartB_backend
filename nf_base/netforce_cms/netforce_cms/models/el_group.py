# Copyright (c) 2012-2015 Netforce Co. Ltd.

from netforce.model import Model, fields

class Group(Model):
    _name = "el.group"
    _string = "Element Group"
    _fields = {
        "name": fields.Char("Group Name",required=True),
        "code": fields.Char("Group Code",required=True),
    }
    _order="name"

Group.register()
