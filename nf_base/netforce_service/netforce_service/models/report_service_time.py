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


class ReportServiceTime(Model):
    _name = "report.service.time"
    _store = False

    def get_project_time(self, context={}):
        db = get_connection()
        res = db.query("SELECT id,name FROM project WHERE state='in_progress' ORDER BY name")
        projects = {}
        for r in res:
            projects[r.id] = {
                "name": r.name,
                "weeks": {},
            }
        res = db.query(
            "SELECT project_id,week,SUM(actual_hours) AS total_actual_hours,SUM(bill_hours) AS total_bill_hours FROM work_time JOIN service_resource r ON r.id=resource_id WHERE state='approved' AND r.type='person' GROUP BY project_id,week")
        for r in res:
            proj = projects.get(r.project_id)
            if not proj:
                continue
            proj["weeks"][r.week] = {
                "actual_hours": r.total_actual_hours,
                "bill_hours": r.total_bill_hours,
            }
        weeks = []
        d = datetime.today()
        d -= timedelta(d.weekday())
        i = 0
        while i < 8:
            weeks.append(d.strftime("%Y-%m-%d"))
            d -= timedelta(days=7)
            i += 1
        #print("weeks", weeks)
        lines = []
        for proj_id, proj in projects.items():
            line = {
                "project_name": proj["name"],
                "weeks": [],
                "older": {
                    "actual_hours": 0,
                    "bill_hours": 0,
                },
                "total_actual_hours": 0,
                "total_bill_hours": 0,
            }
            for w in weeks:
                vals = proj["weeks"].get(w, {"actual_hours":0,"bill_hours":0})
                line["weeks"].append(vals)
            for w, vals in proj["weeks"].items():
                line["total_actual_hours"] += vals["actual_hours"]
                line["total_bill_hours"] += vals["bill_hours"]
                if w < weeks[-1]:
                    line["older"]["actual_hours"] += vals["actual_hours"]
                    line["older"]["bill_hours"] += vals["bill_hours"]
            lines.append(line)
        data = {
            "lines": lines,
        }
        #print("data", data)
        return data

    def get_resource_time(self, context={}):
        db = get_connection()
        res = db.query("SELECT id,name FROM service_resource WHERE type='person' ORDER BY name")
        resources = {}
        for r in res:
            resources[r.id] = {
                "name": r.name,
                "weeks": {},
            }
        res = db.query(
            "SELECT resource_id,week,SUM(actual_hours) AS total_actual_hours,SUM(bill_hours) AS total_bill_hours FROM work_time JOIN service_resource r ON r.id=resource_id WHERE state='approved' AND r.type='person' GROUP BY resource_id,week")
        for r in res:
            resource = resources.get(r.resource_id)
            if not resource:
                continue
            resource["weeks"][r.week] = {
                "actual_hours": r.total_actual_hours or 0,
                "bill_hours": r.total_bill_hours or 0,
            }
        weeks = []
        d = datetime.today()
        d -= timedelta(d.weekday())
        i = 0
        while i < 8:
            weeks.append(d.strftime("%Y-%m-%d"))
            d -= timedelta(days=7)
            i += 1
        #print("weeks", weeks)
        lines = []
        for resource_id, resource in resources.items():
            line = {
                "resource_name": resource["name"],
                "weeks": [],
                "older": {
                    "actual_hours": 0,
                    "bill_hours": 0,
                },
                "total_actual_hours": 0,
                "total_bill_hours": 0,
            }
            for w in weeks:
                vals = resource["weeks"].get(w, {"actual_hours":0,"bill_hours":0})
                line["weeks"].append(vals)
            for w, vals in resource["weeks"].items():
                line["total_actual_hours"] += vals["actual_hours"]
                line["total_bill_hours"] += vals["bill_hours"]
                if w < weeks[-1]:
                    line["older"]["actual_hours"]+=vals["actual_hours"]
                    line["older"]["bill_hours"]+=vals["bill_hours"]
            lines.append(line)
        lines.sort(key=lambda l: l["resource_name"])
        data = {
            "lines": lines,
        }
        #print("data", data)
        return data

ReportServiceTime.register()
