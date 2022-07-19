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

from .model import get_model
from .database import get_active_db
import os
from lxml import etree
import json
from . import module
import shutil
import pkg_resources
import py_compile
import sys
from pprint import pprint

_xml_layouts = {}


def load_xml_layouts():
    print("loading layouts...")
    _xml_layouts.clear()
    loaded_modules = module.get_loaded_modules()
    for m in loaded_modules:
        if not pkg_resources.resource_exists(m, "layouts"):
            continue
        for fname in pkg_resources.resource_listdir(m, "layouts"):
            if not fname.endswith("xml"):
                continue
            data = pkg_resources.resource_string(m, "layouts/" + fname)
            try:
                root = etree.fromstring(data)
                vals = {
                    "module": m,
                }
                vals["name"] = fname.replace(".xml", "")
                vals["type"] = root.tag.lower()
                if root.attrib.get("model"):
                    vals["model"] = root.attrib["model"]
                if root.attrib.get("inherit"):
                    vals["inherit"] = root.attrib["inherit"]
                if root.attrib.get("priority"):
                    vals["priority"] = int(root.attrib["priority"])
                vals["layout"] = data.decode()
                _xml_layouts[vals["name"]] = vals
            except Exception as e:
                print("ERROR: Failed to load XML layout: %s/%s (%s)" % (m, fname, e))
    print("  %d layouts loaded"%len(_xml_layouts))

def load_db_layouts():
    print("load_db_layouts")
    dbname=get_active_db()
    if not dbname:
        return
    layouts={}
    for obj in get_model("view.layout").search_browse([]):
        vals={
            "name": obj.name, 
            "type": obj.type,
            "layout": obj.layout,
        }
        if obj.inherit:
            vals["inherit"]=obj.inherit
        if obj.model_id:
            vals["model"]=obj.model_id.name
        layouts[obj.name]=vals
    print("=> db layouts")
    pprint(layouts)
    return layouts

def layouts_to_json(modules=None,mobile_only=None):
    layouts={}
    layouts.update(_xml_layouts)
    db_layouts=load_db_layouts()
    if db_layouts:
        layouts.update(db_layouts)
    if modules:
        layouts={n:v for n,v in layouts.items() if v.get("module") in modules}
    if mobile_only: 
        layouts={n:v for n,v in layouts.items() if v.get("type") in ("menu_mobile","list_mobile","form_mobile")}
    return layouts
