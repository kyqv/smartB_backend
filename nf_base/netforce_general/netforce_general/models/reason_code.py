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
from netforce import access


class ReasonCode(Model):
    _name = "reason.code"
    _string = "Reason Code"
    _fields = {
        "type": fields.Selection([["fault", "Fault Code"], ["service_multi_visit", "Service Multi-Visit"], ["service_late_response", "Service Late Response"], ["lost_sale_opport", "Lost Sales Opportunity"], ["cancel_sale_opport","Canceled Sales Opportunity"], ["sale_return","Sales Return"], ["lead_refer","Referred Lead"]], "Reason Type", search=True, required=True),
        "code": fields.Char("Code", search=True),
        "name": fields.Char("Name", required=True, search=True),
        "description": fields.Text("Description"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
    }
    _order = "type,code"

ReasonCode.register()
