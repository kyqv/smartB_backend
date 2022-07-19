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
from netforce import database
from netforce import static
from netforce import ipc


class Language(Model):
    _name = "language"
    _string = "Language"
    _key = ["code"]
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "code": fields.Char("Code", required=True),
        "num_translations": fields.Integer("Number of translations", function="get_num_translations"),
        "translations": fields.One2Many("translation","lang_id","Translations"),
        "active": fields.Boolean("Active"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "sequence": fields.Integer("Sequence"),
    }
    _order="sequence"
    _defaults = {
        "active": True,
    }

    def create(self, vals, **kw):
        res = super().create(vals, **kw)
        static.clear_translations()
        ipc.send_signal("clear_ui_params_cache")
        return res

    def write(self, ids, vals, **kw):
        super().write(ids, vals, **kw)
        static.clear_translations()
        ipc.send_signal("clear_ui_params_cache")

    def delete(self, ids, **kw):
        super().delete(ids, **kw)
        static.clear_translations()
        ipc.send_signal("clear_ui_params_cache")

    def get_num_translations(self, ids, context={}):
        db = database.get_connection()
        res = db.query(
            "SELECT lang_id,COUNT(*) AS num FROM translation WHERE lang_id IN %s GROUP BY lang_id", tuple(ids))
        vals = {r.lang_id: r.num for r in res}
        return vals

    def get_active_langs(self):
        db = database.get_connection()
        res = db.query("SELECT code,name FROM language WHERE active=true ORDER BY name")
        active_langs = [dict(r) for r in res]
        return active_langs

    def languages_to_json(self,context={}):
        data=[]
        for obj in self.search_browse([]):
            data.append({
                "name": obj.name,
                "code": obj.code,
            })
        return data

Language.register()
