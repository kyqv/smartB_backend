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
import time


class BarcodeOps(Model):
    _name = "barcode.ops"
    _transient = True
    _fields = {
        "production_id": fields.Many2One("production.order", "Production Order", condition=[["state", "=", "in_progress"]]),
        "workcenter_id": fields.Many2One("workcenter", "Workcenter"),
    }

    def start(self, ids, context={}):
        obj = self.browse(ids)[0]
        order = obj.production_id
        found = False
        for op in order.operations:
            if op.workcenter_id.id == obj.workcenter_id.id:
                found = True
                if op.time_start:
                    raise Exception("Start time already recorded for workcenter %s in production order %s" %
                                    (obj.workcenter_id.code, order.number))
                op.write({"time_start": time.strftime("%Y-%m-%d %H:%M:%S")})
                break
        if not found:
            raise Exception("Workcenter %s not found in production order %s" % (obj.workcenter_id.name, order.number))
        obj.write({
            "production_id": None,
            "workcenter_id": None,
        })
        return {
            "flash": "Operation start time recorded successfully",
            "focus_field": "production_id",
        }

    def stop(self, ids, context={}):
        obj = self.browse(ids)[0]
        order = obj.production_id
        found = False
        for op in order.operations:
            if op.workcenter_id.id == obj.workcenter_id.id:
                found = True
                if not op.time_start:
                    raise Exception("Start time not yet recorded for workcenter %s in production order %s" %
                                    (obj.workcenter_id.code, order.number))
                if op.time_stop:
                    raise Exception("Stop time already recorded for workcenter %s in production order %s" %
                                    (obj.workcenter_id.code, order.number))
                op.write({"time_stop": time.strftime("%Y-%m-%d %H:%M:%S")})
                break
        if not found:
            raise Exception("Workcenter %s not found in production order %s" % (obj.workcenter_id.code, order.number))
        obj.write({
            "production_id": None,
            "workcenter_id": None,
        })
        return {
            "flash": "Operation stop time recorded successfully",
            "focus_field": "production_id",
        }

BarcodeOps.register()
