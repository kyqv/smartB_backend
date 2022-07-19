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

from netforce.controller import Controller
from netforce.model import get_model
from netforce import database
from netforce import access
import json

class Export(Controller):
    _path="/export"

    def get(self):
        model=self.get_argument("model")
        field_paths=json.loads(self.get_argument("field_paths"))
        res=self.get_argument("ids",None)
        if res:
            ids=json.loads(res)
        else:
            ids=None
            res=self.get_argument("condition",None)
            condition=json.loads(res) if res else []
        dbname=self.get_argument("database",None)
        if dbname:
            database.set_active_db(dbname)
        # TODO: user,token
        with database.Transaction():
            if ids is None:
                ids=get_model(model).search(condition)
            csv_data=get_model(model).export_data(ids,field_paths)
        filename="export.csv"
        self.set_header("Content-Disposition","attachment; filename=%s"%filename)
        self.set_header("Content-Type","text/csv")
        self.write(csv_data)

Export.register()
