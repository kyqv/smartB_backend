# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from netforce.model import Model, fields, get_model
from datetime import *
from dateutil.relativedelta import *


class ReportBankSum(Model):
    _name = "report.bank.sum"
    _store = False
    _fields = {
        "date_from": fields.Date("From"),
        "date_to": fields.Date("To"),
    }
    _defaults = {
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
    }

    def get_data(self, context={}):
        data = {
            "company_name": context["company_name"],
        }
        return data

ReportBankSum.register()
