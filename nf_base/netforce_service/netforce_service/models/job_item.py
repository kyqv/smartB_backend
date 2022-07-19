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


class JobItem(Model):
    _name = "job.item"
    _audit_log = True
    _fields = {
        "job_id": fields.Many2One("job", "Service Order", required=True, on_delete="cascade"),
        "service_item_id": fields.Many2One("service.item", "Service Item", required=True),
        "description": fields.Text("Description"),
        "fault_code_id": fields.Many2One("fault.code", "Fault Code"),  # XXX: deprecated
        "fault_reason_id": fields.Many2One("reason.code", "Fault Code", condition=[["type", "=", "fault"]]),
        "counter": fields.Integer("Counter"),
    }
    _order = "job_id.number desc"

JobItem.register()
