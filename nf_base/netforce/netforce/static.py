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

import tornado.web
import mimetypes
from . import module
import os
import distutils.dir_util
import pkg_resources
import hashlib
from . import locale
from io import StringIO
from . import database
import json
from netforce.model import get_model, models_to_json
import glob
from netforce import model
from netforce import layout
from netforce import action
from netforce import template
import netforce
import tempfile
from netforce import config
from netforce.database import get_connection
from netforce import utils
from .access import get_active_user, set_active_user
import netforce

mimetypes.add_type("application/x-font-woff", ".woff")
mimetypes.add_type("application/x-font-woff", ".woff2")
mimetypes.add_type("font/opentype", ".ttf")
mimetypes.add_type("text/cache-manifest", ".appcache")
mimetypes.add_type("text/plain", ".log")


def get_static_data(path,req):
    print("get_static_data", path)
    static_dir=config.get("static_dir") or "static"
    fs_path=os.path.join(static_dir,path)
    if os.path.exists(fs_path):
        data = open(fs_path, "rb").read()
        return data
    data = module.read_module_file("static/" + path)
    if data:
        # if not config.DEV_MODE:
        #    write_static_data(path,data)
        return data
    comps = path.split("/")
    if comps[0] == "db" and comps[2] == "themes": # XXX
        theme_name = comps[3]
        file_path = "/".join(comps[4:])
        db = database.get_connection()
        try:
            data = get_theme_static_data(theme_name, file_path)
            db.commit()
        except:
            db.rollback()
        if data:
            if not config.DEV_MODE:
                write_static_data(path, data)
            return data
    raise Exception("Static file not found: %s" % path)


def write_static_data(path, data):
    print("write_static_data", path)
    static_dir=config.get("static_dir") or "static"
    fs_path=os.path.join(static_dir,path)
    dirname = os.path.dirname(fs_path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    open(fs_path, "wb").write(data)


def get_theme_static_data(theme_name, path):
    print("get_theme_static_data", theme_name, path)
    db = database.get_connection()
    if not db:
        return None
    res = db.get("SELECT file FROM cms_theme WHERE name=%s", theme_name)
    if not res:
        return None
    if res.file:
        zip_path = utils.get_file_path(res.file)
        zip_data = open(zip_path, "rb").read()
        f = BytesIO(zip_data)
        zf = zipfile.ZipFile(f)
        try:
            data = zf.read("static/" + path)
            return data
        except:
            return None
    else:
        data = module.read_module_file("themes/" + theme_name + "/static/" + path)
        if data:
            return data
    return None


class StaticHandler(tornado.web.StaticFileHandler):

    def get(self, path, **kwargs):
        try:
            mime_type, encoding = mimetypes.guess_type(path)
            self.set_header("Content-Type", mime_type)
            data = get_static_data(path,self.request)
            self.write(data)
        except Exception as e:
            print("ERROR: failed to get static file (%s)" % path)
            import traceback
            traceback.print_exc()

    def compute_etag(self):  # XXX
        return None


def export_module_file(m, mod_path, fs_path):
    print("export_module_file", m, mod_path, fs_path)
    if pkg_resources.resource_isdir(m, mod_path):
        print("dir")
        if not os.path.exists(fs_path):
            os.makedirs(fs_path)
        for f in pkg_resources.resource_listdir(m, mod_path):
            if not f:
                continue
            export_module_file(m, mod_path + "/" + f, fs_path + "/" + f)
    else:
        print("file")
        data = pkg_resources.resource_string(m, mod_path)
        open(fs_path, "wb").write(data)


def export_module_file_all(mod_path, fs_path):
    print("export_module_file_all", mod_path, fs_path)
    loaded_modules = module.get_loaded_modules()
    for m in loaded_modules:
        if not pkg_resources.resource_exists(m, mod_path):
            continue
        export_module_file(m, mod_path, fs_path)

def export_static():
    static_dir=config.get("static_dir") or "static"
    export_module_file_all("static",static_dir)
    export_module_file_all("reports",os.path.join(static_dir,"reports"))


def make_ui_params():
    print("building ui_params...")
    data = {}
    data["version"] = netforce.get_module_version_name()
    data["models"] = model.models_to_json()
    data["actions"] = action.actions_to_json()
    data["layouts"] = layout.layouts_to_json()
    data["templates"] = template.templates_to_json()
    if data:
        static_dir=config.get("static_dir") or "static"
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)
        print("  => static/ui_params.json")
        s = json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))
        fs_path=os.path.join(static_dir,"ui_params.json")
        open(fs_path, "w").write(s)


def check_ui_params_db():
    dbname = database.get_active_db()
    if not dbname:
        return ""
    static_dir=config.get("static_dir") or "static"
    fs_path=os.path.join(static_dir,"db/%s/ui_params_db.json"%dbname)
    res = glob.glob(fs_path)
    if not res:
        make_ui_params_db()


def make_ui_params_db():
    print("building ui_params_db...")
    user_id = get_active_user()
    set_active_user(1)
    try:
        data = {}
        data["active_languages"] = get_model("language").get_active_langs()
        trans = {}
        db = database.get_connection()
        res = db.query("SELECT l.code,t.original,t.translation FROM translation t JOIN language l ON l.id=t.lang_id")
        for r in res:
            trans.setdefault(r.code, {})[r.original] = r.translation
        data["translations"] = trans
        settings = get_model("settings").browse(1)
        data["date_format"] = settings.date_format or "YYYY-MM-DD"
        data["use_buddhist_date"] = settings.use_buddhist_date and True or False
        res = db.query("SELECT action FROM inline_help")
        data["inline_help"] = {r.action: True for r in res}
        data["layouts"] = get_model("view.layout").layouts_to_json()
        data["actions"] = get_model("action").actions_to_json()
        data["menu_icon"] = settings.menu_icon
        dbname = database.get_active_db()
        static_dir=config.get("static_dir") or "static"
        fs_path=os.path.join(static_dir,"db/%s/ui_params_db.json" % dbname)
        dir_name=os.path.dirname(fs_path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        s = json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))
        print("  => %s"%fs_path)
        open(fs_path, "w").write(s)
    finally:
        set_active_user(user_id)


def clear_translations():
    print("clear_translations")
    dbname = database.get_active_db()
    static_dir=config.get("static_dir") or "static"
    fs_path=os.path.join(static_dir,"db/%s/ui_params_db.json"%dbname)
    res = glob.glob(fs_path)
    for f in res:
        os.remove(f)
