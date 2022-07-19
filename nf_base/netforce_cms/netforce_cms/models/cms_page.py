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
from netforce import access


class Page(Model):
    _name = "cms.page"
    _string = "Page"
    _name_field = "title"
    _fields = {
        "title": fields.Char("Title", required=True, translate=True,search=True),
        "code": fields.Char("Code", required=True,search=True),
        "body": fields.Text("Body", translate=True),
        "blocks": fields.One2Many("cms.block", "related_id", "Blocks"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "meta_description": fields.Char("Meta Description"),
        "meta_keywords": fields.Char("Meta Keywords"),
        "template": fields.Char("Template"),
        "state": fields.Selection([["active", "Active"], ["inactive", "Inactive"]], "Status", required=True),
        "user_id": fields.Many2One("base.user","User"),
    }
    _defaults = {
        "state": "active",
        "user_id": lambda *a: access.get_active_user(),
    }

Page.register()
