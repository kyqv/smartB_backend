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
import zipfile
import json
import base64
import os
from netforce import database
import time
from collections import OrderedDict
from lxml import etree


class Module(Model):
    _name = "module"
    _string = "Module"
    _key = ["name"]
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "description": fields.Text("Description"),
        "version": fields.Char("Version"),
        "author": fields.Char("Author"),
        "models": fields.One2Many("model", "module_id", "Models"),
        "fields": fields.One2Many("field", "module_id", "Fields"),
        "view_layouts": fields.One2Many("view.layout", "module_id", "View Layouts"),
        "actions": fields.One2Many("action", "module_id", "Actions"),
        "templates": fields.One2Many("template", "module_id", "Templates"),
        "scripts": fields.One2Many("script", "module_id", "Scripts"),
    }
    _order = "name"

    def export_zip(self, ids, context={}):
        t = time.strftime("%Y-%m-%dT%H:%M:%S")
        if len(ids) == 1:
            obj = self.browse(ids)[0]
            fname = obj.name + "-" + t + ".zip"
        else:
            fname = "modules-" + t + ".zip"
        dbname = database.get_active_db()
        fdir = "static/db/" + dbname + "/files"
        if not os.path.exists(fdir):
            os.makedirs(fdir)
        zpath = fdir + "/" + fname
        zf = zipfile.ZipFile(zpath, "w")
        for obj in self.browse(ids):
            vals = OrderedDict()
            vals["name"] = obj.name
            if obj.description:
                vals["description"] = obj.description
            if obj.version:
                vals["version"] = obj.version
            if obj.author:
                vals["author"] = obj.author
            data = json.dumps(vals, indent=4, separators=(',', ': '))
            path = obj.name + "/module.json"
            zf.writestr(path, data)
            for action in obj.actions:
                vals = OrderedDict()
                vals["name"] = action.name
                if action.view:
                    vals["view"] = action.view
                if action.string:
                    vals["string"] = action.string
                if action.model_id:
                    vals["model"] = action.model_id.name
                if action.view_layout_id:
                    vals["view_layout"] = action.view_layout_id.name
                if action.menu_id:
                    vals["menu"] = action.menu_id.name
                if action.options:
                    vals["options"] = json.loads(action.options)
                data = json.dumps(vals, indent=4, separators=(',', ': '))
                path = obj.name + "/actions/" + action.name + ".json"
                zf.writestr(path, data)
            for layout in obj.view_layouts:
                root = etree.fromstring(layout.layout)
                if layout.model_id:
                    root.attrib["model"] = layout.model_id.name
                if layout.inherit:
                    root.attrib["inherit"] = layout.inherit
                data = etree.tostring(root, pretty_print=True)
                path = obj.name + "/layouts/" + layout.name + ".xml"
                zf.writestr(path, data)
            for template in obj.templates:
                data = template.template
                path = obj.name + "/templates/" + template.name + ".hbs"
                zf.writestr(path, data)
            for model in obj.models:
                root = etree.Element("model")
                root.attrib["name"] = model.name
                if model.string:
                    root.attrib["string"] = model.string
                if model.order:
                    root.attrib["order"] = model.order
                for field in model.fields:
                    if field.module_id and field.module_id.id != obj.id:
                        continue
                    el = etree.SubElement(root, "field")
                    el.attrib["name"] = field.name
                    el.attrib["string"] = field.string
                    el.attrib["type"] = field.type
                    if field.relation_id:
                        el.attrib["relation"] = field.relation_id.name
                    if field.relfield_id:
                        el.attrib["relfield"] = field.relfield_id.name
                    if field.selection:
                        el.attrib["selection"] = field.selection
                    if field.required:
                        el.attrib["required"] = "1"
                    if field.readonly:
                        el.attrib["readonly"] = "1"
                    if field.search:
                        el.attrib["search"] = "1"
                    if field.function:
                        el.attrib["function"] = field.function
                    if field.default:
                        el.attrib["default"] = field.default
                    if field.condition:
                        el.attrib["condition"] = field.condition
                data = etree.tostring(root, pretty_print=True)
                path = obj.name + "/models/" + model.name.replace(".", "_") + ".xml"
                zf.writestr(path, data)
            for script in obj.scripts:
                if script.language == "js":
                    path = obj.name + "/scripts/" + script.name + ".js"
                elif script.language == "py":
                    path = obj.name + "/scripts/" + script.name + ".py"
                else:
                    raise Exception("Invalid language in script %s" % script.name)
                zf.writestr(path, script.code)
        zf.close()
        return {
            "next": {
                "type": "download",
                "url": zpath,
            }
        }

    def delete_modules(self, ids, context={}):
        print("Module.delete_modules", ids)
        for obj in self.browse(ids):
            obj.scripts.delete()
            obj.templates.delete()
            obj.actions.delete()
            obj.view_layouts.delete()
            obj.fields.delete()
            obj.models.delete()
            obj.delete()
        return {
            "next": {
                "name": "module",
            },
            "flash": "Modules deleted successfully",
        }

Module.register()
