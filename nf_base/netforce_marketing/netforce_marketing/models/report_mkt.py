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
import time
from datetime import *
from pprint import pprint


def get_months(num_months):
    months = []
    d = date.today()
    m = d.month
    y = d.year
    months.append((y, m))
    for i in range(num_months - 1):
        if (m > 1):
            m -= 1
        else:
            m = 12
            y -= 1
        months.append((y, m))
    return reversed(months)


class ReportMkt(Model):
    _name = "report.mkt"
    _store = False

    def get_leads_per_month(self, context={}):
        db = get_connection()
        res = db.query(
            "SELECT to_char(date,'YYYY-MM') AS month,COUNT(*) as num FROM sale_lead WHERE state!='canceled' GROUP BY month")
        num_leads = {}
        for r in res:
            num_leads[r.month] = r.num
        data = []
        months = get_months(6)
        for y, m in months:
            num = num_leads.get("%d-%.2d" % (y, m), 0)
            d = date(year=y, month=m, day=1)
            data.append((d.strftime("%B"), num))
        return {"value": data}

ReportMkt.register()
