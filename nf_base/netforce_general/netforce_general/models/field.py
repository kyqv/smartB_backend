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

from netforce.model import Model, fields
from netforce import ipc


class Field(Model):
    _name = "field"
    _string = "Field"
    _name_field = "string"
    _key=["model_id","name"]
    _fields = {
        "model_id": fields.Many2One("model", "Model", required=True, on_delete="cascade", search=True),
        "name": fields.Char("Field Code", required=True, search=True, index=True),
        "string": fields.Char("Field Label", required=True, search=True),
        "type": fields.Selection([["char", "Char"], ["text", "Text"], ["decimal", "Decimal"], ["integer", "Integer"], ["date", "Date"], ["datetime", "Datetime"], ["selection", "Selection"], ["boolean", "Boolean"], ["file", "File"], ["many2one", "Many2One"], ["one2many", "One2Many"], ["many2many", "Many2Many"], ["reference", "Reference"]], "Type", search=True),
        "relation_id": fields.Many2One("model", "Relation"),
        "relfield_id": fields.Many2One("field", "Relation Field"),
        "required": fields.Boolean("Required"),
        "readonly": fields.Boolean("Readonly"),
        "unique": fields.Boolean("Unique"),
        "store": fields.Boolean("Stored"),
        "function": fields.Char("Function",search=True),
        "function_multi": fields.Boolean("Multi Function"),
        "selection": fields.Char("Selection", size=8192),
        "default": fields.Char("Default", size=1024),
        "search": fields.Boolean("Search"),
        "stored": fields.Boolean("Stored"),
        "description": fields.Text("Description"),
        "condition": fields.Char("Condition", size=256),
        "module_id": fields.Many2One("module", "Module"),  # XXX: deprecated
        "delete_cascade": fields.Boolean("On Delete Cascade"),
    }
    _order = "model_id.name,name"

    def name_get(self, ids, context={}):
        vals = []
        for obj in self.browse(ids):
            name = "%s / %s" % (obj.model_id.string, obj.string)
            vals.append([obj.id, name])
        return vals

    def find_field(self, model, field, context={}):
        res = self.search([["model_id.name", "=", model], ["name", "=", field]])
        if not res:
            raise Exception("Field not found (%s / %s)" % (model, field))
        return res[0]

    def create(self, *a, **kw):
        new_id = super().create(*a, **kw)
        ipc.send_signal("clear_ui_params_cache")
        return new_id

    def write(self, *a, **kw):
        res = super().write(*a, **kw)
        ipc.send_signal("clear_ui_params_cache")

    def delete(self, *a, **kw):
        res = super().delete(*a, **kw)
        ipc.send_signal("clear_ui_params_cache")

Field.register()
