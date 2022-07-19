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

from netforce import module
import pkg_resources
import os

def templates_to_json(modules=None):
    templates={}
    if modules is None:
        modules=module.get_loaded_modules()
    for m in modules:
        if not pkg_resources.resource_exists(m, "templates"):
            continue
        for fname in pkg_resources.resource_listdir(m, "templates"):
            if fname.endswith(".hbs"):
                tmpl_type="hbs"
            elif fname.endswith(".jsx"):
                tmpl_type="jsx"
            else:
                continue
            tmpl_name = os.path.splitext(fname)[0]
            tmpl_src = pkg_resources.resource_string(m, "templates/" + fname).decode("utf-8")
            templates[tmpl_name]={
                "type":  tmpl_type,
                "body": tmpl_src,
            }
    return templates
