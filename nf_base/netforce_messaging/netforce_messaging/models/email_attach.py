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
from netforce import utils
import time
import json


class EmailAttach(Model):
    _name = "email.attach"
    _string = "Email Attachment"
    _fields = {
        "email_id": fields.Many2One("email.message", "Email", required=True, on_delete="cascade"),
        "file": fields.File("File", required=True),
    }

    def copy_to_doc(self,ids,context={}):
        for obj in self.browse(ids):
            if not obj.file:
                continue
            files=[obj.file]
            title=utils.remove_filename_random(obj.file)
            vals={
                "title": title,
                "files": json.dumps(files),
            }
            email=obj.email_id
            rel=email.related_id
            if rel:
                vals["related_id"]="%s,%s"%(rel._model,rel.id)
            doc_id=get_model("document").create(vals)
        return {
            "next": {
                "name": "doc_doc",
                "mode": "form",
                "active_id": doc_id,
            }
        }

EmailAttach.register()
