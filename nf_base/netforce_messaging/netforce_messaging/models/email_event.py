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


class EmailEvent(Model):
    _name = "email.event"
    _string = "Email Event"
    _fields = {
        "email_id": fields.Many2One("email.message", "Email", required=True, on_delete="cascade"),
        "type": fields.Selection([["accepted", "Accepted"], ["rejected", "Rejected"], ["delivered", "Delivered"], ["failed", "Failed"], ["opened", "Opened"], ["clicked", "Clicked"], ["unsubscribed", "Unsubscribed"], ["complained", "Complained"], ["stored", "Stored"]], "Event Type", required=True),
        "date": fields.DateTime("Date", required=True),
        "ip_addr": fields.Char("IP Address"),
        "location": fields.Char("Location"),
        "user_agent": fields.Char("User Agent", size=1024),
        "url": fields.Char("URL", size=1024),
        "details": fields.Text("Details"),
    }
    _order = "date"
    _defaults = {
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

EmailEvent.register()
