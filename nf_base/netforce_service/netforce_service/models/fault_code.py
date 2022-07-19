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

# XXX: deprecated, use reason codes instead


class FaultCode(Model):
    _name = "fault.code"
    _string = "Fault Code"
    _name_field = "code"
    _fields = {
        "code": fields.Char("Fault Code", required=True, search=True),
        "description": fields.Char("Description", search=True),
    }
    _order = "code"

    def name_get(self, ids, context={}):
        vals = []
        for obj in self.browse(ids):
            name = "%s" % (obj.code)
            if obj.description:
                name += " [%s]" % (obj.description)
            vals.append((obj.id, name))
        return vals

    def name_search(self, name, condition=None, context={}, **kw):
        cond = [["code", "ilike", "%" + name + "%"]]
        if condition:
            cond = [cond, condition]
        ids1 = self.search(cond)
        cond = [["description", "ilike", "%" + name + "%"]]
        if condition:
            cond = [cond, condition]
        ids2 = self.search(cond)
        ids = list(set(ids1 + ids2))
        return self.name_get(ids, context=context)

FaultCode.register()
