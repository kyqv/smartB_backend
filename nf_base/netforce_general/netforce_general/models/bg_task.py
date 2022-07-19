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
from netforce import database
from netforce import tasks
from datetime import *
import time


class Task(Model):
    _name = "bg.task"
    _string = "Background Task"
    _fields = {
        "date": fields.DateTime("Scheduled Date",search=True,required=True),
        "model": fields.Char("Model",search=True),
        "method": fields.Char("Method",search=True),
        "args": fields.Text("Arguments"),
        "state": fields.Selection([["waiting", "Waiting"], ["done", "Done"], ["canceled", "Canceled"], ["error", "Error"]], "Status", required=True,search=True),
        "error_message": fields.Text("Error Message"),
        "result": fields.Text("Result"),
        "timeout": fields.Integer("Timeout (s)"),
        "cron_job_id": fields.Many2One("cron.job","Cron Job",search=True),
        "wkf_rule_id": fields.Many2One("wkf.rule","Workflow Rules"), # XXX: deprecated
        "start_time": fields.DateTime("Start Time"),
        "end_time": fields.DateTime("End Time"),
        "user_id": fields.Many2One("base.user","User"),
        "company_id": fields.Many2One("company","Company"),
    }
    _order = "date desc,id desc"
    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "state": "waiting",
    }

    def create(self, vals, context={}, **kw):
        new_id = super().create(vals, **kw)
        self.delete_old_tasks()
        if not context.get("no_notif"):
            tasks.notify_task()
        return new_id

    def write(self, ids, vals, context={}, **kw):
        super().write(ids, vals, **kw)
        if not context.get("no_notif"):
            tasks.notify_task()

    def delete_old_tasks(self,context={}):
        min_date=(datetime.now()-timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        db=database.get_connection()
        db.execute("DELETE FROM bg_task WHERE date<%s",min_date)

Task.register()
