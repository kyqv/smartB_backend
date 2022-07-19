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
from netforce import ipc
import os
import netforce


def _clear_cache():
    print("clear template cache pid=%s" % os.getpid())
    netforce.template.clear_template_cache()

ipc.set_signal_handler("clear_template_cache", _clear_cache)


class Template(Model):
    _name = "template"
    _string = "Template"
    _key = ["name","theme_id"]
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "template": fields.Text("Template"),
        "theme_id": fields.Many2One("theme","Theme"),
        "module_id": fields.Many2One("module", "Module"),
    }
    _order = "name"

    def create(self, vals, **kw):
        res = super().create(vals, **kw)
        ipc.send_signal("clear_template_cache")
        return res

    def write(self, ids, vals, **kw):
        super().write(ids, vals, **kw)
        ipc.send_signal("clear_template_cache")

    def delete(self, ids, **kw):
        super().delete(ids, **kw)
        ipc.send_signal("clear_template_cache")

Template.register()
