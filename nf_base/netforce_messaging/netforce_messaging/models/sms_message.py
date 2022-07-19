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
from netforce import access
import time
import requests
import boto3

class SmsMessage(Model):
    _name = "sms.message"
    _string = "SMS Message"
    _name_field = "sender"
    _fields = {
        "account_id": fields.Many2One("sms.account", "SMS Account"),
        "date": fields.DateTime("Date", required=True, search=True),
        "phone": fields.Char("Phone Number", required=True, size=256, search=True),
        "body": fields.Text("Body", search=True),
        "state": fields.Selection([["draft", "Draft"], ["to_send", "To Send"], ["sent", "Sent"], ["error", "Error"]], "Status", required=True, search=True),
        "error": fields.Text("Error Message"),
        "num_chars": fields.Integer("Number Of Characters",function="get_num_chars"),
    }
    _order = "date desc"
    _defaults = {
        "state": "draft",
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    def to_send(self, ids, context={}):
        for obj in self.browse(ids):
            obj.write({"state": "to_send"})

    def send(self,ids,context={}):
        print("SMSMessage.send",ids)
        for obj in self.browse(ids):
            try:
                acc=obj.account_id
                if not acc:
                    res=get_model("sms.account").search([])
                    if not res:
                        raise Exception("Missing account in SMS %s"%obj.id)
                    acc_id=res[0]
                    obj.write({"account_id":acc_id})
                    obj=obj.browse()[0]
                if acc.type=="aws":
                    obj.send_aws()
                elif acc.type=="twilio":
                    obj.send_twilio()
                elif acc.type=="nexmo":
                    obj.send_nexmo()
                elif acc.type=="thaibulksms":
                    obj.send_thaibulksms()
                elif acc.type=="smsmkt":
                    obj.send_smsmkt()
                else:
                    raise Exception("Invalid SMS account type: %s"%acc.type)
            except Exception as e:
                import traceback
                traceback.print_exc()
                pass

    def send_aws(self,ids,context={}):
        obj=self.browse(ids[0])
        try:
            acc=obj.account_id
            client=boto3.client("sns",aws_access_key_id=acc.user,aws_secret_access_key=acc.password)
            number = obj.phone
            sns.publish(PhoneNumber = number, Message=body)
            obj.write({"state": "sent"})
        except Exception as e:
            obj.write({"state": "error"})
            obj.write({"state": "error","error":str(e)})

    def send_twilio(self,ids,context={}):
        obj=self.browse(ids[0])
        try:
            acc=obj.account_id
            url="https://api.twilio.com/2010-04-01/Accounts/%s/Messages"%acc.username
            params={
                "To": obj.phone,
                "From": acc.sender,
                "Body": obj.body,
            }
            r=requests.post(url,data=params,auth=(acc.username,acc.password))
            if r.status_code!=201:
                raise Exception("Failed to send SMS with Twilio (status_code=%s)"%r.status_code)
            obj.write({"state": "sent"})
        except Exception as e:
            obj.write({"state": "error"})
            obj.write({"state": "error","error":str(e)})

    def send_thaibulksms(self,ids,context={}):
        obj=self.browse(ids[0])
        try:
            acc=obj.account_id
            url = "https://secure.thaibulksms.com/sms_api.php"
            params={
                'username': acc.username,
                'password': acc.password,
                'msisdn': obj.phone,
                'message': obj.body[:160].encode('tis-620'),
            }
            if acc.sender:
                params['sender']=acc.sender
            print("params",params)
            r=requests.post(url,data=params)
            if r.text.find("<Status>1</Status>") == -1:
                raise Exception("Failed to send SMS with ThaiBulkSMS: %s"%r.text)
            obj.write({"state": "sent"})
        except Exception as e:
            obj.write({"state": "error","error":str(e)})

    def send_smsmkt(self,ids,context={}):
        obj=self.browse(ids[0])
        try:
            acc=obj.account_id
            url="https://member.smsmkt.com/SMSLink/SendMsg/index.php"
            params={
                "Username": acc.username,
                "Password": acc.password,
                "Msnlist": obj.phone,
                'Msg': obj.body,
                "Sender": acc.sender,
            }
            url+="?User=%(Username)s&Password=%(Password)s&Msnlist=%(Msnlist)s&Msg=%(Msg)s&Sender=%(Sender)s"%params
            r=requests.get(url,timeout=15)
            if r.status_code!=200:
                raise Exception("Failed to send SMS")
            obj.write({"state": "sent"})
        except Exception as e:
            obj.write({"state": "error","error":str(e)})

    def send_from_template(self, template=None, state=None, context={}):
        if not template:
            raise Exception("Missing template")
        res = get_model("sms.template").search([["name", "=", template]])
        if not res:
            raise Exception("Template not found: %s" % template)
        tmpl_id = res[0]
        trigger_model = context.get("trigger_model")
        if not trigger_model:
            raise Exception("Missing trigger model")
        tm = get_model(trigger_model)
        trigger_ids = context.get("trigger_ids")
        if trigger_ids is None:
            raise Exception("Missing trigger ids")
        user_id = access.get_active_user()
        if user_id:
            user = get_model("base.user").browse(user_id)
        else:
            user = None
        for obj in tm.browse(trigger_ids):
            tmpl_ctx = {"obj": obj, "user": user, "context": context}
            get_model("sms.template").create_sms([tmpl_id],tmpl_ctx,state=state)
        self.send_messages_async()

    def send_messages(self,context={}):
        for obj in self.search_browse([["state","=","to_send"]],context=context):
            obj.send()

    def send_messages_async(self, context={}):
        vals={
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": "sms.message",
            "method": "send_messages",
        }
        get_model("bg.task").create(vals)

    def get_num_chars(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=len(obj.body or "")
        return vals

SmsMessage.register()
