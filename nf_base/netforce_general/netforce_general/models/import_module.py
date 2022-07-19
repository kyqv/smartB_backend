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
import zipfile
import json
from lxml import etree
from netforce import utils
import os


class ImportModule(Model):
    _name = "import.module"
    _transient = True
    _fields = {
        "file": fields.File("Zip File"),
    }

    def do_import(self, ids, context={}):
        print("import modules")
        obj = self.browse(ids)[0]
        path = utils.get_file_path(obj.file)
        zf = zipfile.ZipFile(path, "r")
        modules = {}
        for n in zf.namelist():
            if not n.endswith("/module.json"):
                continue
            path = n[:-len("/module.json")]
            data = zf.read(n).decode()
            vals = json.loads(data)
            name = vals["name"]
            module = {
                "name": name,
                "path": path,
                "info": vals,
                "model_files": [],
                "layout_files": [],
                "action_files": [],
                "template_files": [],
                "script_files": [],
            }
            modules[name] = module
        if not modules:
            raise Exception("No modules found")
        print("modules", modules.keys())

        ids = get_model("module").search([["name", "in", modules.keys()]])
        get_model("module").delete_modules(ids)

        for name, module in modules.items():
            info = module["info"]
            vals = {
                "name": name,
                "description": info.get("description"),
                "version": info.get("version"),
                "author": info.get("author"),
            }
            get_model("module").create(vals)

        for path in zf.namelist():
            found = False
            for name, module in modules.items():
                if path.startswith(module["path"] + "/"):
                    path2 = path[len(module["path"]) + 1:]
                    module = modules[name]
                    found = True
                    break
            if not found:
                continue
            if path2.startswith("models/") and path2.endswith(".xml"):
                module["model_files"].append(path)
            elif path2.startswith("layouts/") and path2.endswith(".xml"):
                module["layout_files"].append(path)
            elif path2.startswith("actions/") and path2.endswith(".json"):
                module["action_files"].append(path)
            elif path2.startswith("templates/") and path2.endswith(".hbs"):
                module["template_files"].append(path)
            elif path2.startswith("scripts/") and path2.endswith(".js"):
                module["script_files"].append(path)

        for mod_name, module in modules.items():
            for path in module["model_files"]:
                print("import model", path)
                n = os.path.splitext(os.path.basename(path))[0]
                data = zf.read(path).decode()
                root = etree.fromstring(data)
                vals = {
                    "name": root.attrib["name"],
                    "module_id": get_model("module").get(mod_name, require=True),
                }
                if root.attrib.get("string"):
                    vals["string"] = root.attrib["string"]
                if root.attrib.get("description"):  # XXX
                    vals["description"] = root.attrib["description"]
                res = get_model("model").search([["name", "=", vals["name"]]])
                if res:
                    model_id = res[0]
                    get_model("model").write([model_id], vals)
                else:
                    model_id = get_model("model").create(vals)

        def _import_field(el, model, mod_name):
            vals = {
                "model_id": get_model("model").get(model, require=True),
                "module_id": get_model("module").get(mod_name, require=True),
                "name": el.attrib["name"],
                "string": el.attrib["string"],
                "type": el.attrib["type"],
            }
            if el.attrib.get("relation"):
                vals["relation_id"] = get_model("model").get(el.attrib["relation"], require=True)
            if el.attrib.get("relfield"):
                vals["relfield_id"] = get_model("field").find_field(el.attrib["relation"], el.attrib["relfield"])
            if el.attrib.get("selection"):
                vals["selection"] = el.attrib["selection"]
            if el.attrib.get("required"):
                vals["required"] = True
            if el.attrib.get("readonly"):
                vals["readonly"] = True
            if el.attrib.get("function"):
                vals["function"] = el.attrib["function"]
            if el.attrib.get("default"):
                vals["default"] = el.attrib["default"]
            if el.attrib.get("search"):
                vals["search"] = True
            if el.attrib.get("condition"):
                vals["condition"] = el.attrib["condition"]
            if el.attrib.get("description"):
                vals["description"] = el.attrib["description"]
            get_model("field").create(vals)

        for mod_name, module in modules.items():
            for path in module["model_files"]:
                print("import fields #1", path)
                n = os.path.splitext(os.path.basename(path))[0]
                data = zf.read(path).decode()
                root = etree.fromstring(data)
                for el in root:
                    if el.tag != "field":
                        continue
                    if el.attrib.get("relfield"):
                        continue
                    _import_field(el, root.attrib["name"], mod_name)

        for mod_name, module in modules.items():
            for path in module["model_files"]:
                print("import fields #2", path)
                n = os.path.splitext(os.path.basename(path))[0]
                data = zf.read(path).decode()
                root = etree.fromstring(data)
                for el in root:
                    if el.tag != "field":
                        continue
                    if not el.attrib.get("relfield"):
                        continue
                    _import_field(el, root.attrib["name"], mod_name)

        for mod_name, module in modules.items():
            for path in module["layout_files"]:
                print("import layout", path)
                n = os.path.splitext(os.path.basename(path))[0]
                data = zf.read(path).decode()
                root = etree.fromstring(data)
                vals = {
                    "name": n,
                    "module_id": get_model("module").get(mod_name, require=True),
                    "type": root.tag.lower(),
                }
                if root.attrib.get("model"):
                    vals["model_id"] = get_model("model").get(root.attrib["model"], require=True)
                    del root.attrib["model"]
                if root.attrib.get("inherit"):
                    vals["inherit"] = root.attrib["inherit"]
                    del root.attrib["inherit"]
                vals["layout"] = etree.tostring(root, pretty_print=True).decode()
                get_model("view.layout").create(vals)

        for mod_name, module in modules.items():
            for path in module["action_files"]:
                print("import action", path)
                n = os.path.splitext(os.path.basename(path))[0]
                data = zf.read(path).decode()
                vals = json.loads(data)
                vals2 = {
                    "name": n,
                    "module_id": get_model("module").get(mod_name, require=True),
                }
                if vals.get("string"):
                    vals2["string"] = vals["string"]
                if vals.get("view"):
                    vals2["view"] = vals["view"]
                if vals.get("model"):
                    vals2["model_id"] = get_model("model").get(vals["model"], require=True)
                if vals.get("view_layout"):
                    vals2["view_layout_id"] = get_model("view.layout").get(vals["view_layout"], require=True)
                if vals.get("menu"):
                    vals2["menu_id"] = get_model("view.layout").get(vals["menu"], require=True)
                if vals.get("options"):
                    vals2["options"] = json.dumps(vals["options"])
                get_model("action").create(vals2)

        for mod_name, module in modules.items():
            for path in module["template_files"]:
                print("import template", path)
                n = os.path.splitext(os.path.basename(path))[0]
                data = zf.read(path).decode()
                vals = {
                    "name": n,
                    "module_id": get_model("module").get(mod_name, require=True),
                    "template": data,
                }
                get_model("template").create(vals)

        for mod_name, module in modules.items():
            for path in module["script_files"]:
                print("import script", path)
                n = os.path.splitext(os.path.basename(path))[0]
                data = zf.read(path).decode()
                vals = {
                    "name": n,
                    "module_id": get_model("module").get(mod_name, require=True),
                    "code": data,
                }
                get_model("script").create(vals)

        return {
            "next": {
                "name": "module",
            },
            "flash": "Modules imported successfully",
        }

ImportModule.register()
