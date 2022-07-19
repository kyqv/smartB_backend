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
import os.path
from netforce.database import get_active_db


class Import(Model):
    _name = "import.data"
    _transient = True
    _fields = {
        "model": fields.Char("Model", required=True),
        "next": fields.Char("Next"),
        "title": fields.Char("Title"),
        "file": fields.File("File to import", required=True),
    }

    def get_data(self, context={}):
        model = context["import_model"]
        m = get_model(model)
        title = "Import"
        if m._string:
            title += " " + m._string
        return {
            "model": model,
            "title": title,
            "next": context.get("next"),
        }

    def do_import(self, ids, context={}):
        obj = self.browse(ids[0])
        #dbname = get_active_db()
        #data = open(os.path.join("static", "db", dbname, "files", obj.file), "rU", errors="replace").read()
        m = get_model(obj.model)
        #m.import_data(data)
        m.import_csv(obj.file)
        if obj.next:
            return {
                "next": {
                    "name": obj.next,
                },
                "flash": "Data imported successfully",
            }

Import.register()
