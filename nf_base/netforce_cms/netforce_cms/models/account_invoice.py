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
import time
from netforce import config
from netforce.database import get_connection
from netforec.logger import audit_log
import urllib


class Invoice(Model):
    _inherit = "account.invoice"
    _fields = {
        "number": fields.Char("Number"),
    }

    def check_payment_online(self, ids, context={}):
        obj = self.browse(ids)[0]
        date = time.strftime('%Y%m%d%H%M%S')
        qs = urllib.parse.urlencode([
            ('mid', 1000006741),
            ('terminal', 524114384),
            ('command', 'CRINQ'),
            ('ref_no', obj.number),
            ('ref_date', date),
            ('service_id', 10),
            ('cur_abbr', 'THB'),
            ('amount', obj.amount_total),
        ])

        url = 'https://nsips-test.scb.co.th:443/NSIPSWeb/NsipsMessageAction.do?'
        data = qs.encode('utf-8')
        req = urllib.request.Request(url, data)
        response = urllib.request.urlopen(req)
        ur = response.read()
        te = ur.decode('utf-8')
        p = urllib.parse.parse_qsl(te)
        params = dict(list(map(lambda x: (x[0], x[1]), p)))
        payment_status = params['payment_status'] or ''
        amount = params['amount'] or ''
        trans_no = params['trans_no'] or ''
        if payment_status == "002":
            try:
                db = get_connection()
                vals = {
                    "type": "in",
                    "pay_type": "invoice",
                    "contact_id": obj.contact_id.id,
                    "date": time.strftime("%Y-%m-%d"),
                    "ref": trans_no,
                    "account_id": obj.account_id.id,
                    "currency_id": obj.currency_id.id,
                    "lines": [("create", {
                        "type": "invoice",
                        "invoice_id": obj.id,
                        "account_id": obj.account_id.id,
                        "amount": amount,
                    })]
                }
                pmt_id = get_model("account.payment").create(vals, context={"type": vals["type"]})
                get_model("account.payment").post([pmt_id])
                db.commit()
            except Exception as e:
                db = get_connection()
                db.rollback
                import traceback
                audit_log("Failed to get result payment from scb", details=traceback.format_exc())
                traceback.print_exc()
