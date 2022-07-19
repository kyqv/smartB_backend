# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from netforce.model import Model, fields, get_model
from datetime import *
from dateutil.relativedelta import *


class ReportIncomeContact(Model):
    _name = "report.income.contact"
    _store = False
    _fields = {
        "date": fields.Date("Date"),
    }
    _defaults = {
        "date": lambda *a: date.today().strftime("%Y-%m-01"),
    }

    def get_data(self, context={}):
        data = {
            "company_name": context["company_name"],
        }
        return data

ReportIncomeContact.register()
