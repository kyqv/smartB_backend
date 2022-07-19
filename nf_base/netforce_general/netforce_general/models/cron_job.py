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
from netforce.database import get_connection
from datetime import *
import time
import json


class CronJob(Model):
    _name = "cron.job"
    _string = "Cron Job"
    _fields = {
        "name": fields.Char("Description", required=True),
        "date": fields.DateTime("Scheduled Date"),
        "model": fields.Char("Model"),
        "method": fields.Char("Method"),
        "args": fields.Text("Arguments"),
        "state": fields.Selection([["active", "Active"], ["inactive", "Inactive"]], "Status", required=True),
        "interval_num": fields.Integer("Interval Number"),
        "interval_type": fields.Selection([["second", "Second"], ["minute", "Minute"], ["hour", "Hour"], ["day", "Day"]], "Interval Unit"),
        "call_num": fields.Integer("Number Of Calls"), # XXX: deprecated
        "date_start": fields.DateTime("Start Date"), # XXX: deprecated
        "date_stop": fields.DateTime("Stop Date"), # XXX: deprecated
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "last_error_time": fields.DateTime("Last Error Time"), # XXX: deprecated
        "error_message": fields.Text("Error Message"), # XXX: deprecated
        "timeout": fields.Integer("Timeout (s)"),
        "tasks": fields.One2Many("bg.task","cron_job_id","Task Queue"),
    }
    _order = "name"
    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "state": "active",
    }

    def create(self, vals, **kw):
        new_id = super().create(vals, **kw)
        return new_id

    def write(self, ids, vals, **kw):
        super().write(ids, vals, **kw)

    def schedule_job(self, model, method, *args):
        vals = {
            "name": "/",
            "model": model,
            "method": method,
            "args": json.dumps(args),
        }
        return self.create(vals)

    def trigger_event(self, event, context={}):
        print("CronJob.trigger_event", event)
        db = get_connection()
        res = db.query(
            "SELECT DISTINCT(tm.name) AS trigger_model FROM wkf_rule r,model tm WHERE tm.id=r.trigger_model_id AND r.trigger_event=%s AND r.state='active'", event)
        models = sorted([r.trigger_model for r in res])
        for model in models:
            m = get_model(model)
            m.trigger(None, event)

    def get_alert(self, context={}):
        res = self.search([["state", "=", "error"]])
        if not res:
            return None
        return {
            "type": "error",
            "title": "WARNING",
            "text": "There are scheduled jobs with 'Error' status",
        }

    def update_dates(self,ids,context={}):
        for obj in self.browse(ids):
            if obj.interval_type == "second":
                dt = timedelta(seconds=obj.interval_num or 1)
            elif obj.interval_type == "minute":
                dt = timedelta(minutes=obj.interval_num or 1)
            elif obj.interval_type == "hour":
                dt = timedelta(hours=obj.interval_num or 1)
            #elif obj.interval_type == "day":
            else:
                dt = timedelta(days=obj.interval_num or 1)
            #else:
            #    raise Exception("Missing interval unit")
            next_date = datetime.strptime(obj.date, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            while next_date <= now:  # TODO: make this faster
                next_date += dt
            obj.write({"date": next_date.strftime("%Y-%m-%d %H:%M:%S")})

    def create_tasks(self,ids,context={}):
        now=time.strftime("%Y-%m-%d %H:%M:%S")
        for obj in self.browse(ids):
            if obj.state!="active":
                continue
            if obj.tasks:
                task=obj.tasks[0]
                if task.state=="waiting":
                    continue
            if obj.date<=now:
                obj.update_dates()
                obj=obj.browse()[0]
            vals={
                "date": obj.date,
                "model": obj.model,
                "method": obj.method,
                "args": obj.args,
                "state": "waiting",
                "cron_job_id": obj.id,
            }
            get_model("bg.task").create(vals,context=context)
            

CronJob.register()
