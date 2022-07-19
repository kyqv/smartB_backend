# Copyright (c) 2012-2015 Netforce Co. Ltd.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

from netforce.model import Model, fields, get_model


class LinkListItem(Model):
    _name = "cms.linklist.item"
    _fields = {
        "list_id": fields.Many2One("cms.linklist", "Link List", required=True, on_delete="cascade"),
        "sequence": fields.Integer("Sequence"),
        "title": fields.Char("Title", required=True, translate=True),
        "type": fields.Selection([["menu", "Menu"], ["submenu", "Submenu"]], "Type", required=True),
        "url": fields.Char("URL", required=True, size=256),
        "sub_items": fields.One2Many("cms.linklist.item", None, "Sub Items", function="get_sub_items"),
    }
    _defaults = {
        "type": "menu",
    }
    _order = "list_id,sequence,id"

    def get_sub_items(self, ids, context={}):
        list_ids = []
        for obj in self.browse(ids):
            list_ids.append(obj.list_id.id)
        list_ids = list(set(list_ids))
        sub_items = {}
        for lst in get_model("cms.linklist").browse(list_ids):
            parent_id = None
            for item in lst.items:
                if item.type == "menu":
                    sub_items[item.id] = []
                    parent_id = item.id
                elif item.type == "submenu":
                    sub_items[parent_id].append(item.id)
        return {id: sub_items[id] for id in ids}

LinkListItem.register()
