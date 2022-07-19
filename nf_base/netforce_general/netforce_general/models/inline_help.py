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
from netforce import static
import time


class InlineHelp(Model):
    _name = "inline.help"
    _string = "Help Item"
    _fields = {
        "action": fields.Char("Action Name", required=True, search=True),
        "title": fields.Char("Help Title", required=True, search=True),
        "content": fields.Text("Help Content", required=True, search=True),
        "hide": fields.Boolean("Hide"),
        "create_date": fields.DateTime("Date Created"),
        "modif_date": fields.DateTime("Date Modified"),
    }
    _order = "title"
    _defaults = {
        "create_date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "modif_date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    def create(self, vals, **kw):
        res = super().create(vals, **kw)
        static.clear_translations()  # XXX: rename this
        return res

    def write(self, ids, vals, **kw):
        super().write(ids, vals, **kw)
        static.clear_translations()  # XXX: rename this

    def delete(self, ids, **kw):
        super().delete(ids, **kw)
        static.clear_translations()  # XXX: rename this

InlineHelp.register()
