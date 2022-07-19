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
from netforce.database import get_active_db
from netforce.static import export_module_file_all
from netforce import utils
from netforce import ipc
import netforce.template
import os
import zipfile
from netforce import module
import pkg_resources

class Theme(Model):
    _name = "theme"
    _string = "Theme"
    _fields = {
        "name": fields.Char("Name", required=True),
        "description": fields.Text("Description"),
        "file": fields.File("ZIP File"),
        "templates": fields.One2Many("template","theme_id","Templates"),
    }
    _defaults = {
        "state": "inactive",
    }

    def activate(self, ids, context={}):
        obj = self.browse(ids)[0]
        all_ids = self.search([])
        self.write(all_ids, {"state": "inactive"})
        obj.write({"state": "active"})
        obj.update()

    def update(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.export_static_files()
        obj.load_templates()

    def export_static_files(self, ids, context={}):
        obj = self.browse(ids)[0]
        theme = obj.name
        dbname = get_active_db()
        if obj.file:
            zip_path = utils.get_file_path(obj.file)
            zf = zipfile.ZipFile(zip_path)
            for n in zf.namelist():
                if not n.startswith("static/"):
                    continue
                if n[-1] == "/":
                    continue
                n2 = n[7:]
                if n2.find("..") != -1:
                    continue
                data = zf.read(n)
                f_path = "static/db/" + dbname + "/themes/" + theme + "/" + n2
                dir_path = os.path.dirname(f_path)
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                print("export file", f_path)
                open(f_path, "wb").write(data)
        else:
            export_module_file_all("themes/" + theme + "/static", "static/db/" + dbname + "/themes/" + theme)

    def load_templates(self, ids, context={}):
        obj = self.browse(ids[0])
        if obj.file:
            zip_path = utils.get_file_path(obj.file)
            zf = zipfile.ZipFile(zip_path)
            for n in zf.namelist():
                if not n.startswith("templates/"):
                    continue
                if not n.endswith(".hbs"):
                    continue
                n2 = n[10:-4]
                if n2.find("..") != -1:
                    continue
                print("load template", n2)
                data = zf.read(n)
                vals = {
                    "name": n2,
                    "template": data.decode(),
                    "theme_id": obj.id,
                }
                get_model("template").merge(vals)
        else:
            theme = obj.name
            loaded_modules = module.get_loaded_modules()
            for m in reversed(loaded_modules):
                if not pkg_resources.resource_isdir(m, "themes/" + theme + "/templates"):
                    continue
                for f in pkg_resources.resource_listdir(m, "themes/" + theme + "/templates"):
                    if not f.endswith(".hbs"):
                        continue
                    f2 = f[:-4]
                    print("load template", f2)
                    data = pkg_resources.resource_string(m, "themes/" + theme + "/templates/" + f)
                    vals = {
                        "name": f2,
                        "template": data.decode(),
                        "theme_id": obj.id,
                    }
                    get_model("template").merge(vals)

Theme.register()
