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
from pprint import pprint

def js_time(s):
    d=datetime.strptime(s,"%Y-%m-%d %H:%M:%S")
    return time.mktime(d.timetuple()) * 1000

def js_date(s):
    d=datetime.strptime(s,"%Y-%m-%d")
    return time.mktime(d.timetuple()) * 1000

class ReportIssue(Model):
    _name = "report.issue"
    _store = False

    def get_issue_chart(self, context={}):
        actions=[]
        for issue in get_model("issue").search_browse([]):
            if issue.date_created:
                actions.append((issue.date_created,"open"))
            if issue.state=="closed" and issue.date_closed:
                actions.append((issue.date_closed,"close"))
        actions.sort()
        values=[]
        num_issues=0
        for d,action in actions:
            if action=="open":
                num_issues+=1
            elif action=="close":
                num_issues-=1
            values.append((js_time(d), num_issues))
        data = {
            "value": values, 
        }
        return data

    def get_issue_close_chart(self, context={}):
        closed={}
        for issue in get_model("issue").search_browse([["state","=","closed"],["date_closed","!=",None]]):
            d=issue.date_closed[:10]
            closed.setdefault(d,0)
            closed[d]+=1
        values=[]
        for d,n in sorted(closed.items()):
            values.append((js_date(d), n))
        data = {
            "value": [{
                "key": "Closed",
                "values": values,
            }]
        }
        pprint(data)
        return data

ReportIssue.register()
