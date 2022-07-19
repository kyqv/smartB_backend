from netforce.model import Model, fields, get_model
from netforce.utils import get_data_path

class MenuAccessAdd(Model):
    _name = "menu.access.add"
    _transient = True
    _fields = {
        "menu_access_id": fields.Many2One("menu.access","Menu Access",required=True,on_delete="cascade"),
        "profile_id": fields.Many2One("profile","Profile"),
        "user_id": fields.Many2One("base.user","User"),
        "action": fields.Char("Action", search=True),
        "menu": fields.Char("Menu", search=True),
        "parent_menu": fields.Char("Parent Menu", search=True),
        "button": fields.Char("Button", search=True),
        "label": fields.Char("Label", search=True),
        "access":fields.Selection([["hidden","Hidden"],["visible","Visible"]],"Access"),
    }

    def _get_fields_data(self, refer_id, item, context={}):
        res = get_model("menu.access").browse(refer_id)
        if item == "profile_id" and res.profile_id:
            result = res.profile_id.id
        elif item == "user_id" and res.user_id:
            result = res.user_id.id
        elif item == "action" and res.action:
            result = res.action
        elif item == "menu" and res.menu:
            result = res.menu
        elif item == "parent_menu" and res.parent_menu:
            result = res.parent_menu
        elif item == "button" and res.button:
            result = res.button
        elif item == "label" and res.label:
            result = res.label
        elif item == "access" and res.access:
            result = res.access
        else:
            result = None
        return result

    _defaults={
        "menu_access_id": lambda self,ctx: ctx["refer_id"] if ctx.get("refer_id") else None,
        "profile_id": lambda self,ctx: self._get_fields_data(ctx["refer_id"],"profile_id") if ctx.get("refer_id") else None,
        "user_id": lambda self,ctx: self._get_fields_data(ctx["refer_id"],"user_id") if ctx.get("refer_id") else None,
        "action": lambda self,ctx: self._get_fields_data(ctx["refer_id"],"action") if ctx.get("refer_id") else None,
        "menu": lambda self,ctx: self._get_fields_data(ctx["refer_id"],"menu") if ctx.get("refer_id") else None,
        "parent_menu": lambda self,ctx: self._get_fields_data(ctx["refer_id"], "parent_menu") if ctx.get("refer_id") else None,
        "button": lambda self,ctx: self._get_fields_data(ctx["refer_id"],"button") if ctx.get("refer_id") else None,
        "label": lambda self,ctx: self._get_fields_data(ctx["refer_id"],"label") if ctx.get("refer_id") else None,
        "access": lambda self,ctx: self._get_fields_data(ctx["refer_id"],"access") if ctx.get("refer_id") else None,
    }

    def duplicate_menu_access(self,ids,context={}):
        print("menu.access.duplicate",ids)
        obj = self.browse(ids[0])
        vals = {
            "menu_access_id": obj.menu_access_id.id if obj.menu_access_id else None,
            "profile_id": obj.profile_id.id if obj.profile_id else None,
            "user_id": obj.user_id.id if obj.user_id else None,
            "action": obj.action,
            "menu": obj.menu,
            "parent_menu": obj.parent_menu,
            "button": obj.button,
            "label": obj.label,
            "access": obj.access,
        }
        new_id = get_model("menu.access").create(vals)
        return {
            "next":{
                "name": "menu_access",
                "mode": "form",
                "active_id": new_id,
                "target": "new_window",
            },
            "flash": "Menu access duplicated.",
        }

MenuAccessAdd.register()
