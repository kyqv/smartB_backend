from netforce.model import Model, fields, get_model
from netforce.utils import get_data_path

class FieldAccessAdd(Model):
    _name = "field.access.add"
    _transient = True
    _fields = {
        "field_access_id": fields.Many2One("field.access","Field Access",required=True,on_delete="cascade"),
        "profile_id": fields.Many2One("profile","Profile"),
        "user_id": fields.Many2One("base.user","User"),
        "model_id": fields.Many2One("model", "Model", required=True, on_delete="cascade", search=True),
        "field_id": fields.Many2One("field", "Field", on_delete="cascade", search=True),
        "access": fields.Selection([["readwrite","Read/Write"], ["readonly", "Read-Only"], ["hidden","Hidden"]], "Access"),
    }

    def _get_fields_data(self, refer_id, item, context={}):
        res = get_model("field.access").browse(refer_id)
        if item == "profile_id" and res.profile_id:
            result = res.profile_id.id
        elif item == "user_id" and res.user_id:
            result = res.user_id.id
        elif item == "model_id" and res.model_id:
            result = res.model_id.id
        elif item == "field_id" and res.field_id:
            result = res.field_id.id
        elif item == "access" and res.access:
            result = res.access
        else:
            result = None
        return result

    _defaults={
        "field_access_id": lambda self,ctx: ctx["refer_id"] if ctx.get("refer_id") else None,
        "profile_id": lambda self,ctx: self._get_fields_data(ctx["refer_id"],"profile_id") if ctx.get("refer_id") else None,
        "user_id": lambda self,ctx: self._get_fields_data(ctx["refer_id"],"user_id") if ctx.get("refer_id") else None,
        "model_id": lambda self,ctx: self._get_fields_data(ctx["refer_id"],"model_id") if ctx.get("refer_id") else None,
        "field_id": lambda self,ctx: self._get_fields_data(ctx["refer_id"],"field_id") if ctx.get("refer_id") else None,
        "access": lambda self,ctx: self._get_fields_data(ctx["refer_id"],"access")if ctx.get("refer_id") else None,
    }

    def duplicate_field_access(self,ids,context={}):
        print("field.access.duplicate",ids)
        obj = self.browse(ids[0])
        vals = {
            "field_access_id": obj.field_access_id.id if obj.field_access_id else None,
            "profile_id": obj.profile_id.id if obj.profile_id else None,
            "user_id": obj.user_id.id if obj.user_id else None,
            "model_id": obj.model_id.id if obj.model_id else None,
            "field_id": obj.field_id.id if obj.field_id else None,
            "access": obj.access,
        }
        new_id = get_model("field.access").create(vals)
        return {
            "flash": "Field access duplicated.",
        }

FieldAccessAdd.register()
