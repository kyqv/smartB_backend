from netforce.model import Model, fields, get_model
import time
import random


class VerifRequest(Model):
    _name = "verif.request"
    _string = "Verification Request"
    _fields = {
        "time": fields.DateTime("Time",required=True),
        "phone": fields.Char("Phone"),
        "state": fields.Selection([["new","New"],["sent","Sent"],["verified","Verified"]],"Status",required=True),
        "verif_code": fields.Char("Verif Code"),
        "ref": fields.Char("Reference"),
    }
    _defaults = {
        "time": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "state": "new",
    }
    _order="time desc"

    def start_verif(self,phone,context={}):
        code="%.4d"%random.randint(0,9999)
        vals={
            "phone": phone,
            "verif_code": code,
        }
        req_id=self.create(vals)
        vals={
            "phone": phone,
            "body": "%s is your verification code"%code,
            "state": "to_send",
        }
        get_model("sms.message").create(vals)
        get_model("sms.message").send_messages_async()
        return {
            "request_id": req_id,
        }

    def check_verif(self,req_id,code,context={}): 
        obj=self.browse(req_id)
        success=code==obj.verif_code
        if success:
            obj.write({"state":"verified"})
        return success

VerifRequest.register()
