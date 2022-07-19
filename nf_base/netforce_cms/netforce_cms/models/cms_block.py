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
from netforce import ipc
from netforce.locale import get_active_locale
from netforce.database import get_active_db
import os

_block_cache = {}


def _clear_cache():
    print("clear block cache (pid=%s)" % os.getpid())
    _block_cache.clear()

ipc.set_signal_handler("clear_block_cache", _clear_cache)


class Block(Model):
    _name = "cms.block"
    _string = "Block"
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "related_id": fields.Reference([["cms.page", "Page"], ["cms.blog.post", "Post"]], "Related To"),
        "html": fields.Text("HTML", search=True, translate=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
    }
    _order = "name"

    def get_block(self, name, page_id=None, post_id=None, context={}):
        # print("get_block",name,page_id,post_id)
        dbname = get_active_db()
        lang = get_active_locale()
        key = (dbname, name, page_id, post_id, lang)
        if key in _block_cache:
            #print("...cache hit")
            return _block_cache[key]
        #print("...cache miss")
        cond = [["name", "=", name]]
        if page_id:
            cond.append(["related_id", "=", "cms.page,%d" % page_id])
        if post_id:
            cond.append(["related_id", "=", "cms.blog.post,%d" % post_id])
        res = self.search(cond)
        if res:
            block = self.read(res, ["html"])[0]
        else:
            block = None
        _block_cache[key] = block
        return block

    def create(self, *a, **kw):
        res = super().create(*a, **kw)
        ipc.send_signal("clear_block_cache")
        return res

    def write(self, *a, **kw):
        res = super().write(*a, **kw)
        ipc.send_signal("clear_block_cache")

    def delete(self, *a, **kw):
        res = super().delete(*a, **kw)
        ipc.send_signal("clear_block_cache")

    def update_block(self,name,content,context={}):
        print("Block.update_block",name)
        res=self.search([["name","=",name]])
        if res:
            block_id=res[0]
        else:
            vals={"name":name}
            block_id=self.create(vals)
        vals={
            "html": content,
        }
        self.write([block_id],vals)

    def read_blocks(self,blocks,context={}):
        print("Block.read_blocks",blocks)
        contents={}
        for obj in self.search_browse([["name","in",blocks]]):
            contents[obj.name]=obj.html
        res={}
        for n in blocks:
            res[n]=contents.get(n)
        return res

Block.register()
