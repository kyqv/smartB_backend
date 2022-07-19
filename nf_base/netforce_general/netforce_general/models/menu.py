# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from netforce.model import Model, fields, get_model
import json


class Menu(Model):
    _name = "menu"
    _string = "Menu"
    _key = ["string"]
    _fields = {
        "string": fields.Char("Menu Label",required=True),
        "sequence": fields.Integer("Sequence"),
        "parent_id": fields.Many2One("menu","Menu"),
        "action": fields.Char("Action"),
    }
    _order = "sequence"

    def get_menu_info(self,context={}):
        n=get_model("chat.message").get_num_unread()
        vals={}
        vals["chat"]={
            "badge": n,
            "tooltip": "You have %s unread chat messages"%n,
        }
        return vals

Menu.register()
