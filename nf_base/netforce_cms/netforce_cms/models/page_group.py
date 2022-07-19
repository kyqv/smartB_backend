# Copyright (c) 2012-2015 Netforce Co. Ltd.

from netforce.model import Model, fields

class PageGroup(Model):
    _name = "page.group"
    _string = "Page Group"
    _fields = {
        "name": fields.Char("Group Name",required=True),
        "code": fields.Char("Group Code"),
    }
    _order="name"

PageGroup.register()
