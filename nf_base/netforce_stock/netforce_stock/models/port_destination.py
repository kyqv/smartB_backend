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


class PortDestination(Model):
    _name = "port.destination"
    _string = "Port Destination"
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "code": fields.Char("Code", required=True, search=True, unique=True),
        "description": fields.Text("Description"),
        "country_id": fields.Many2One("country","Country"),
    }
    _order = "code"

    def name_get(self, ids, context={}):
        print("port.destination.name_get",ids)
        #if len(ids)>1000:
        #    import pdb; pdb.set_trace()
        vals = []
        for obj in self.browse(ids):
            if obj.code:
                name = "[%s] %s" % (obj.code, obj.name)
            else:
                name = obj.name
            vals.append((obj.id, name, obj.image))
        return vals

PortDestination.register()
