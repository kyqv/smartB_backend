# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

from netforce.model import Model, fields, get_model


class ReportAccounts(Model):
    _name = "report.accounts"
    _store = False

    def get_data(self, context={}):
        data = []
        accounts = get_model("account.account").search_browse([])
        for acc in accounts:
            data.append({
                "code": acc.code,
                "name": acc.name,
                "description": acc.description,
                "type": acc.type,
                "tax": acc.tax_id.name,
            })
        return data

ReportAccounts.register()
