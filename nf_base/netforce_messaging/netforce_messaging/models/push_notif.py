from netforce.model import Model, fields, get_model
from netforce import access
import time
import requests

# XXX
SERVER_KEY="AAAAPFhSi2A:APA91bGo-s_FnoZjTxoGXXjTnJqaO2uYo1pfT6yhxabO6sIVD1Ev24WCS-xuaPTUKMbxjSR4Lp9p_q-ob7xbzHFN16BY_jNGQDJaVEUR6wtuF-r2k1t20JK6zv52zkgvC39SA2RDA6Kz"

class PushNotif(Model):
    _name = "push.notif"
    _string = "Push Notif"
    _fields = {
        "time": fields.DateTime("Time", required=True, search=True),
        "device_id": fields.Many2One("device.token","Device",search=True),
        "title": fields.Char("Title",search=True),
        "message": fields.Text("Message",search=True),
        "state": fields.Selection([["draft","Draft"],["to_send","To Send"],["sent","Sent"],["error","Error"]],"Status",required=True),
        "error": fields.Text("Error"),
    }
    _order = "time desc"
    _defaults={
        "time": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "state": "draft",
    }

    def send(self,ids,context={}):
        obj=self.browse(ids[0])
        try:
            headers={
                "Authorization": "key=%s"%SERVER_KEY,
            }
            data={
              "to" : obj.device_id.token,
              "notification": {
                "title": obj.title,
                "body": obj.message,
                "content_available": True,
                "priority" : "high",
                "sound": "default",
                "vibrate": 300,
                "wake_screen": True,
                "leds": True,
              },
              #"data": {
              #    "show_in_foreground": False,
              #}
            }
            url="https://fcm.googleapis.com/fcm/send"
            req=requests.post(url,json=data,headers=headers)
            if req.status_code!=200:
                raise Exception("Invalid status: %s"%req.status_code)
            res=req.json()
            if not res.get("success"):
                raise Exception("Failed to send message: %s"%res)
            obj.write({"state":"sent"})
            return {
                "alert": "Notification sent successfully.",
            }
        except Exception as e:
            obj.write({"state":"error","error":str(e)})

    def send_notifs(self,context={}):
        for obj in self.search_browse([["state","=","to_send"]],context=context):
            obj.send()

    def send_notifs_async(self, context={}):
        vals={
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": "push.notif",
            "method": "send_notifs",
        }
        get_model("bg.task").create(vals)

PushNotif.register()
