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


class ResourceAlloc(Model):
    _name = "service.resource.alloc"
    _string = "Resource Allocation"

    def get_contact(self, ids, context={}):
        res = {}
        for obj in self.browse(ids):
            res[obj.id] = obj.job_id.contact_id.id
        return res

    def get_service_item(self, ids, context={}):
        res = {}
        for obj in self.browse(ids):
            items = obj.job_id.items
            if items:
                service_item_id = items[-1].id
                res[obj.id] = service_item_id
        return res

    _fields = {
        "resource_id": fields.Many2One("service.resource", "Resource", required=True, search=True, on_delete="cascade"),
        "job_id": fields.Many2One("job", "Service Order", required=True, search=True, on_delete="cascade"),
        "time_start": fields.DateTime("Planned Start Time", required=True),
        "time_stop": fields.DateTime("Planned Stop Time", required=True),
        "description": fields.Text("Description"),
        "contact_id": fields.Many2One("contact", "Customer", function="get_contact"),
        "service_item_id": fields.Many2One("service.item", "Service Item", function="get_service_item"),
    }
    _order = "time_start,resource_id.name"

    _constraints = ["check_overlap"]

    def check_overlap(self, ids, context={}):
        for obj in self.browse(ids):
            res = self.search([["id", "!=", obj.id], ["resource_id", "=", obj.resource_id.id],
                               ["time_start", "<", obj.time_stop], ["time_stop", ">", obj.time_start]])
            if res:
                alloc2 = self.browse(res[0])
                raise Exception("Invalid resource allocation for %s, %s overlaps with %s" %
                                (obj.resource_id.name, obj.job_id.number, alloc2.job_id.number))

ResourceAlloc.register()
