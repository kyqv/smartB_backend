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


class FixedAssetType(Model):
    _name = "account.fixed.asset.type"
    _string = "Asset Type"
    _key=["code"]
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "code": fields.Char("Code", required=True, search=True),
        "dep_rate": fields.Decimal("Depreciation Rate (%)", search=True),
        "dep_method": fields.Selection([["line", "Straight Line"], ["decline", "Declining Balance"]], "Depreciation Method", search=True),
        "fixed_asset_account_id": fields.Many2One("account.account", "Fixed Asset Account"),
        "accum_dep_account_id": fields.Many2One("account.account", "Accum. Depr. Account"),
        "dep_exp_account_id": fields.Many2One("account.account", "Depr. Exp. Account"),
        "description": fields.Text("Description"),
    }

FixedAssetType.register()
