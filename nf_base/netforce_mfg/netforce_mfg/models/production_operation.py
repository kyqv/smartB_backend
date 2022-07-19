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
from datetime import *
import math


class Operation(Model):
    _name = "production.operation"
    _string = "Production Operation"
    _fields = {
        "order_id": fields.Many2One("production.order", "Production Order", required=True, on_delete="cascade"),
        "workcenter_id": fields.Many2One("workcenter", "Workcenter", required=True),
        "employee_id": fields.Many2One("hr.employee", "Employee"),
        "planned_duration": fields.Decimal("Planned Duration (Minutes)"),
        "time_start": fields.DateTime("Start Time"),
        "time_stop": fields.DateTime("Stop Time"),
        "actual_duration": fields.Decimal("Actual Duration (Minutes)", function="get_actual_duration"),
        "notes": fields.Text("Notes"),
    }

    def get_actual_duration(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            if obj.time_start and obj.time_stop:
                t0 = datetime.strptime(obj.time_start, "%Y-%m-%d %H:%M:%S")
                t1 = datetime.strptime(obj.time_stop, "%Y-%m-%d %H:%M:%S")
                vals[obj.id] = math.ceil((t1 - t0).total_seconds() / 60.0)
            else:
                vals[obj.id] = None
        return vals

Operation.register()
