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
import time
from netforce.database import get_connection
import json


class FieldValue(Model):
    _name = "field.value"
    _string = "Field Value"
    _fields = {
        "model": fields.Char("Model", index=True, search=True),
        "field": fields.Char("Field", index=True),
        "record_id": fields.Integer("Record ID", index=True, search=True),
        "value": fields.Text("Value"),
        "company_id": fields.Many2One("company", "Company"),
        "language": fields.Char("Language"),
        "model_id": fields.Many2One("model","Model", search=True),
        "inst_id": fields.Many2One("model.inst","Model Instance", search=True),
        "field_id": fields.Many2One("field","Field"),
        "history_id": fields.Many2One("record.history","History",on_delete="cascade"),
    }
    _order="id desc"
    _indexes = [
        ("model", "field", "record_id"),
    ]

    def create(self,vals,context={}):
        field_id=vals.get("field_id")
        if field_id and not vals.get("model_id"):
            field=get_model("field").browse(field_id)
            vals["model_id"]=field.model_id.id
        return super().create(vals)

    def set_fields(self,context={}):
        for obj in self.search_browse([]):
            if obj.field_id:
                obj.write({"field":obj.field_id.name})
            if obj.model_id:
                obj.write({"model":obj.model_id.name})
            if obj.inst_id:
                obj.write({"record_id":obj.inst_id.record_id})

FieldValue.register()
