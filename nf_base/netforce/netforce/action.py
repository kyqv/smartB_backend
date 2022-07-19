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

from . import module
from .model import get_model
from .database import get_active_db
import os.path
import json
import re
import imp
import py_compile
import pkg_resources
import marshal
import types
import shutil
import netforce
import sys
from lxml import etree
from pprint import pprint

_actions = {}


def load_actions():
    print("loading actions...")
    _actions.clear()
    loaded_modules = module.get_loaded_modules()
    for m in loaded_modules:
        if not pkg_resources.resource_exists(m, "actions"):
            continue
        for fname in pkg_resources.resource_listdir(m, "actions"):
            if not fname.endswith("xml"):
                continue
            data = pkg_resources.resource_string(m, "actions/" + fname)
            try:
                root = etree.fromstring(data)
                vals = {
                    "module": m,
                }
                for field in root.iterfind("field"):
                    name = field.attrib["name"]
                    if len(field) > 0:
                        val = etree.tostring(field[0]).decode()
                    else:
                        val = field.text
                    vals[name] = val
                if not vals.get("name"):  # XXX
                    name = os.path.splitext(fname)[0]
                    vals["name"] = name
                _actions[vals["name"]] = vals
            except Exception as e:
                print("ERROR: Failed to load action: %s/%s" % (m, fname))
    print("  %d actions loaded"%len(_actions))

def load_db_actions():
    print("load_db_actions")
    dbname=get_active_db()
    if not dbname:
        return
    actions={}
    for obj in get_model("action").search_browse([]):
        vals={
            "name": obj.name, 
            "string": obj.string,
            "view": obj.view,
        }
        if obj.model_id:
            vals["model"]=obj.model_id.name
        if obj.menu:
            vals["menu"]=obj.menu
        if obj.options:
            try:
                opts=json.loads(obj.options)
                vals.update(opts)
            except Exception as e:
                print("Error: %s"%e)
                continue
        actions[obj.name]=vals
    print("=> db actions")
    pprint(actions)
    return actions

def get_action(name, context={}):
    action = _actions.get(name)
    if action is None:
        raise Exception("Action not found: %s" % name)
    return action


def actions_to_json(modules=None):
    actions={}
    actions.update(_actions)
    db_actions=load_db_actions()
    if db_actions:
        actions.update(db_actions)
    if modules is None:
        return actions
    return {a:v for a,v in actions.items() if v.get("module") in modules}
