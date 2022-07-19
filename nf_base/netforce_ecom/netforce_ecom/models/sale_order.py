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
from netforce.database import get_active_db
import os.path
import requests
import urllib.parse
import time
from lxml import etree
from netforce.access import get_active_company, get_active_user, set_active_user, set_active_company
from datetime import datetime, timedelta
from netforce import access


class SaleOrder(Model):
    _inherit = "sale.order"
    _fields = {
        "ecom_can_cancel": fields.Boolean("Can Cancel", function="get_ecom_can_cancel"),
        "ecom_tax_no": fields.Char("Ecommerce Tax ID"),
        "ecom_tax_branch_no": fields.Char("Ecommerece Branch Tax ID"),
    }

    def get_ecom_can_cancel(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            can = obj.state == "confirmed"
            for pick in obj.pickings:
                if pick.state == "done":
                    can = False
                    break
            vals[obj.id] = can
        return vals

    def ecom_cancel_cart(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.ecom_can_cancel:
            raise Exception("Can not cancel sales order %s" % obj.number)
        for pick in obj.pickings:
            pick.void()
        for inv in obj.invoices:
            if inv.state == "waiting_payment":
                inv.void()
            else:
                inv.copy_to_credit_note(context)
        obj.void()

SaleOrder.register()
