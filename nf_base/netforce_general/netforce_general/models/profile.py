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
from netforce import access


class Profile(Model):
    _name = "profile"
    _string = "Profile"
    _key = ["name"]
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "code": fields.Char("Code"),
        "perms": fields.One2Many("profile.access", "profile_id", "Model Permissions"),
        "field_perms": fields.One2Many("field.access", "profile_id", "Field Permissions"),
        "menu_perms": fields.One2Many("menu.access", "profile_id", "Menu Permissions"),
        "other_perms": fields.Many2Many("permission", "Other Permissions"),
        "home_action": fields.Char("Login Action"),
        "home_action_mobile": fields.Char("Login Action Mobile"),
        "login_company_id": fields.Many2One("company", "Login Company"),
        "prevent_login": fields.Boolean("Prevent Login"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "default_model_perms": fields.Selection([["full", "Full Access"], ["no_delete","Full Access Except Delete"], ["readonly","Read-only Access"], ["no", "No Access"]], "Default Model Permissions"),
        "default_menu_access": fields.Selection([["visible", "Visible"], ["hidden", "Hidden"]], "Default Menu Access"),
        "require_approve": fields.Boolean("Require Approval"),
    }
    _order = "name"
    _defaults = {
        "default_model_perms": "full",
        "default_menu_access": "hidden",
    }

    def get_data(self, context={}):
        vals = {}
        perms = []
        for m in get_model("model").search_browse([]):
            perms.append({
                "model_id": [m.id, m.string],
            })
        vals["perms"] = perms
        return vals

    def copy(self, ids, context={}):
        obj = self.browse(ids)[0]
        vals = {
            "name": obj.name + " (Copy)",
            "perms": [],
            "other_perms": [("set", [p.id for p in obj.other_perms])],
            "home_action": obj.home_action,
        }
        for perm in obj.perms:
            vals["perms"].append(("create", {
                "model_id": perm.model_id.id,
                "perm_read": perm.perm_read,
                "perm_create": perm.perm_create,
                "perm_write": perm.perm_write,
                "perm_delete": perm.perm_delete,
                "view_all": perm.view_all,
                "modif_all": perm.modif_all,
            }))
        profile_id = get_model("profile").create(vals)
        for o in obj.menu_perms:
            o._copy({"profile_id":profile_id})
        for o in obj.field_perms:
            o._copy({"profile_id":profile_id})
        for o in obj.other_perms:
            o._copy({"profile_id":profile_id})
        return {
            "next": {
                "name": "profile",
                "mode": "form",
                "active_id": profile_id,
            },
            "flash": "New profile created",
        }

    def profile_to_json(self,profile_id=None,context={}):
        if not profile_id:
            profile_id=access.get_active_profile()
            if not profile_id:
                return {}
        obj=self.browse(profile_id)
        print("#"*80)
        print("#"*80)
        print("#"*80)
        print("profile_id",profile_id)
        print("user_id",access.get_active_user())
        return {
            "name": obj.name,
            "code": obj.code,
            "prevent_login": obj.prevent_login,
            "default_menu_access": obj.default_menu_access,
            "default_model_perms": obj.default_model_perms,
            "home_action": obj.home_action,
            "home_action_mobile": obj.home_action_mobile,
        }

Profile.register()
