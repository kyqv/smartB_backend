from netforce.controller import Controller
from netforce.model import get_model
from netforce import database
from netforce import access
from netforce import config
from datetime import datetime
import json
import configparser
import os

class Webhook(Controller):
    _path="/shopee_webhook"

    def load_map(self,filename="server.conf"):
        mapping = {}
        if filename:
            #test = open(filename).read()  # XXX: test if have permissions to read
            parser = configparser.ConfigParser()
            parser.read(filename)
            if parser.has_section("shopee_mapping"):
                for k, v in parser.items("shopee_mapping"):
                    mapping[k] = v
        else:
            print("No configuration file found")
        return mapping

    def post(self):
        print("shopee_webhook")
        print("body, %s"%json.loads(self.request.body))
        try:
            mapping = self.load_map()
            body = json.loads(self.request.body)
            shop_id = body.get("shop_id")
            if not shop_id:
                raise Exception("shop_id not found in body")
            dbs = []
            for k,v in mapping.items():
                if str(shop_id) in v:
                    dbs.append(k)
            print("dbs",dbs)
        except Exception as e:
            print(e)
            dbs = ["nfo_demo1"]
        for db in dbs:
            database.set_active_db(db)
            #database.set_active_db("nfo_demo_my") #XXX
            access.set_active_user(1)
            with database.Transaction():
                shopee_settings = get_model("shopee.settings").browse(1)
                if shopee_settings.enable_webhook:
                    webhook_id = get_model("shopee.webhook").create({"date":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"body":json.dumps(json.loads(self.request.body))})
                    get_model("shopee.webhook").handle_webhook([webhook_id])


Webhook.register()
