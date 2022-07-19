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
from netforce import access
from netforce import ipc


class FieldAccess(Model):
    _name = "field.access"
    _string = "Field Access"
    _fields = {
        "profile_id": fields.Many2One("profile", "Profile", on_delete="cascade", search=True),
        "user_id": fields.Many2One("base.user","User"),
        "model_id": fields.Many2One("model", "Model", required=True, on_delete="cascade", search=True),
        "field_id": fields.Many2One("field", "Field", on_delete="cascade", search=True),
        "access": fields.Selection([["readwrite","Read/Write"], ["readonly", "Read-Only"], ["hidden","Hidden"]], "Access"),
    }
    _order = "field_id.model_id.string,field_id.string,profile_id.name"
    _defaults = {
        "access": "readwrite",
    }

    def field_access_to_json(self,profile_id=None,user_id=None,context={}):
        if not profile_id:
            profile_id=access.get_active_profile()
        if not user_id:
            user_id=access.get_active_user()
        data=[]
        added={}
        for obj in self.search_browse([["profile_id","=",profile_id]]):
            if obj.user_id and obj.user_id.id!=user_id:
                continue
            vals={
                "model": obj.field_id.model_id.name,
                "field": obj.field_id.name,
                "access": obj.access,
            }
            k=str(vals)
            if obj.field_id and obj.field_id.model_id:
                data.append(vals)
                added[k]=True
        for obj in self.search_browse([["profile_id","=",None]]):
            if obj.user_id and obj.user_id.id!=user_id:
                continue
            vals={
                "model": obj.field_id.model_id.name,
                "field": obj.field_id.name,
                "access": obj.access,
            }
            k=str(vals)
            if k in added:
                continue
            if obj.field_id and obj.field_id.model_id:
                data.append(vals)
                added[k]=True
        return data

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


FieldAccess.register()
