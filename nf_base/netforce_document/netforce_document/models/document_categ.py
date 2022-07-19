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


class DocumentCateg(Model):
    _name = "document.categ"
    _string = "Document Category"
    _name_field = "full_name"
    _fields = {
        "name": fields.Char("Category Name", required=True, search=True),
        "code": fields.Char("Document Code", search=True),
        "full_name": fields.Char("Category Name", function="get_full_name", search=True, store=True, size=256),
        "parent_id": fields.Many2One("document.categ", "Parent Category"),
        "description": fields.Text("Description", search=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "expire_after": fields.Char("Expire After"),
        "file_name": fields.Char("Filename Format"),
        "reminder_templates": fields.One2Many("reminder.template", "doc_categ_id", "Reminder Templates"),
    }
    _order = "full_name"
    _constraints = ["_check_cycle"]

    def create(self, vals, **kw):
        new_id = super().create(vals, **kw)
        self.function_store([new_id])
        return new_id

    def write(self, ids, vals, **kw):
        super().write(ids, vals, **kw)
        child_ids = self.search(["id", "child_of", ids])
        self.function_store(child_ids)

    def get_full_name(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            names = [obj.name]
            p = obj.parent_id
            while p:
                names.append(p.name)
                p = p.parent_id
            full_name = " / ".join(reversed(names))
            vals[obj.id] = full_name
        return vals

DocumentCateg.register()
