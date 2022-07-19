# Copyright (c) 2012-2015 Netforce Co. Ltd.

from netforce.model import Model, fields

class Style(Model):
    _name = "page.style"
    _string = "Page Style"
    _fields = {
        "name": fields.Char("Style Name",required=True),
        "code": fields.Char("Style Code",required=True),
        "styles": fields.Text("Styles"),
    }
    _order="name"

Style.register()
