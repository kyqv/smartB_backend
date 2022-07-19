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
import uuid
import time
from netforce import database


class Account(Model):
    _name = "sms.account"
    _string = "SMS Account"
    _name_field = "name"
    _fields = {
        "name": fields.Char("Account Name", required=True, search=True),
        "type": fields.Selection([["aws","Amazon SNS"],["twilio","Twilio"],["nexmo","Nexmo"],["thaibulksms","Thai Bulk SMS"],["smsmkt","SMSMKT"]], "Type", required=True),
        "sender": fields.Char("Sender"),
        "username": fields.Char("User", required=True),
        "password": fields.Char("Password", required=True),
        "sequence": fields.Integer("Sequence"),
        "skip_verif": fields.Boolean("Skip SMS Verification"),
    }
    _order="sequence"

Account.register()
