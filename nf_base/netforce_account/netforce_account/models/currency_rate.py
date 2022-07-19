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
import time
from netforce import ipc
from netforce import access


class CurrencyRate(Model):
    _name = "currency.rate"
    _multi_company = True
    _fields = {
        "currency_id": fields.Many2One("currency", "Currency", required=True, on_delete="cascade"),
        "date": fields.Date("Date", required=True),
        "sell_rate": fields.Decimal("Sell Rate", scale=6, required=True),
        "buy_rate": fields.Decimal("Buy Rate", scale=6, required=True),
        "rate": fields.Decimal("Rate", scale=6),  # XXX: deprecated
        "company_id": fields.Many2One("company", "Company"),
    }
    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "company_id": lambda *a: access.get_active_company(),
    }
    _order = "date desc,id desc"

    def create(self, *a, **kw):
        new_id = super().create(*a, **kw)
        ipc.send_signal("clear_currency_cache")
        return new_id

    def write(self, *a, **kw):
        super().write(*a, **kw)
        ipc.send_signal("clear_currency_cache")

    def delete(self, *a, **kw):
        super().delete(*a, **kw)
        ipc.send_signal("clear_currency_cache")

CurrencyRate.register()
