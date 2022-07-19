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
import time


class Attach(Model):
    _name = "attach"
    _string = "Attachment"
    _order = "date desc"
    _fields = {
        "date": fields.DateTime("Date", required=True, search=True),
        "user_id": fields.Many2One("base.user", "User", search=True),
        "file": fields.File("File", required=True),
        "related_id": fields.Reference([["document", "Document"]], "Related To"),
        "description": fields.Text("Description", search=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
    }

    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": lambda self, context: int(context.get("user_id")),
    }

Attach.register()
