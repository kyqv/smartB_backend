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
from netforce import database
from netforce import access
from netforce import action
from netforce import layout
from netforce import model
from netforce import get_module_version_name,get_module_version_code
from netforce import template
import json
import binascii
from netforce import ipc
import os

_cache={}

def _clear_cache():
    pid = os.getpid()
    print("ui_params _clear_cache pid=%s" % pid)
    _cache.clear()

ipc.set_signal_handler("clear_ui_params_cache", _clear_cache)

class UIParams(Model):
    _name = "ui.params"
    _store = False

    def get_hash(self,context={}):
        ui_params=self.load_ui_params(context=context)
        return ui_params["hash"]
    
    def load_ui_params(self,context={}):
        print("UIParams.load_ui_params")
        user_id=access.get_active_user()
        profile_id=access.get_active_profile()
        access.set_active_user(1)
        dbname=database.get_active_db()
        modules_str=str(context.get("modules"))
        translations_only=context.get("translations_only")
        ui_params=_cache.get((dbname,user_id,modules_str,translations_only))
        if ui_params:
            return ui_params
        print("!!! cache miss",dbname)
        settings=get_model("settings").browse(1)
        actions=action.actions_to_json(modules=context.get("modules"))
        layouts=layout.layouts_to_json(modules=context.get("modules"))
        models=model.models_to_json()
        templates=template.templates_to_json(modules=context.get("modules"))
        languages=get_model("language").languages_to_json()
        translations=get_model("translation").translations_to_json()
        #addons=get_model("addon").addons_to_json()
        menu_access=get_model("menu.access").menu_access_to_json(profile_id=profile_id,user_id=user_id)
        field_access=get_model("field.access").field_access_to_json(profile_id=profile_id,user_id=user_id)
        profile=get_model("profile").profile_to_json(profile_id=profile_id)
        print("profile",profile)
        configs=get_model("config").config_to_json(user_id)
        tooltips=get_model("help.tooltip").tooltips_to_json()
        videos=get_model("help.video").videos_to_json(user_id)
        components=get_model("page.layout").components_to_json()
        if translations_only:
            ui_params={
                "languages": languages,
                "translations": translations,
            }
        else:
            ui_params={
                "actions": actions,
                "layouts": layouts,
                "models": models,
                "templates": templates,
                "languages": languages,
                "translations": translations,
                #"addons": addons,
                "menu_access": menu_access,
                "field_access": field_access,
                "profile": profile,
                "configs": configs,
                "tooltips": tooltips,
                "videos": videos,
                "components": components,
                "settings": {
                    "date_format": settings.date_format,
                    "use_buddhist_date": settings.use_buddhist_date,
                }
            }
        buf=json.dumps(ui_params).encode("utf-8")
        crc=binascii.crc32(buf)
        ui_params["hash"]="%08x"%crc
        _cache[(dbname,user_id,modules_str,translations_only)]=ui_params
        return ui_params

    def find_details_action(self,model,active_id,context={}):
        actions=action.actions_to_json()
        found=None
        for name,vals in actions.items():
            if vals.get("model")!=model:
                continue
            if vals.get("view") not in ("list_container","multi_view"):
                continue
            found=name
            break
        if not found:
            return None
        vals={
            "name": found,
            "mode": "form",
            "active_id": active_id,
        }
        return vals

UIParams.register()
