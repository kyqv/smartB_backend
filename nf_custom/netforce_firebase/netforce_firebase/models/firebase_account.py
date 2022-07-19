from netforce.model import Model, fields, get_model
from netforce import config
from netforce import utils
from netforce import database
from netforce import tasks
import requests
import hashlib
import hmac
from datetime import *
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import db

class Account(Model):
    _name = "firebase.account"
    _string = "Firebase Account"
    _fields = {
        "name": fields.Char("Account Name",required=True,search=True),
        "db_url": fields.Char("Database URL"),
        "key_json": fields.Text("Firebase Key (JSON)"),
        "sync_models": fields.One2Many("sync.model","firebase_account_id","Sync Models"),
        "sync_records": fields.One2Many("sync.record","firebase_account_id","Sync Records"),
    }

    def set_creds(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.db_url:
            raise Exception("Missing db url")
        if not obj.key_json:
            raise Exception("Missing key json")
        open("/tmp/firebase_key.json","w").write(obj.key_json) # XXX
        cred = credentials.Certificate("/tmp/firebase_key.json")
        try:
            firebase_admin.initialize_app(cred,{
              "databaseURL": obj.db_url,
            })
        except:
            import traceback
            traceback.print_exc()

    def import_vals(self,model,data):
        m=get_model(model)
        vals={}
        for n,v in data.items():
            f=m._fields.get(n)
            if not f:
                continue
            if isinstance(f,fields.Many2One) and v:
                rm=get_model(f.relation)
                res=rm.search(["or",["sync_id","=",v],["id","=",v]])
                if not res:
                    raise Exception("Record not found: %s %s"%(f.relation,v))
                rid=res[0]
                vals[n]=rid
            else:
                vals[n]=v
        return vals

    def process_event(self,msg,context={}):
        event_type=msg["event_type"]
        path=msg["path"]
        data=msg["data"]
        model=path.split("/")[1].replace("_",".")
        sync_id=path.split("/")[2]
        if event_type=="put":
            if data is not None:
                res=get_model(model).search([["sync_id","=",sync_id]])
                if res:
                    raise Exception("Record already exists: %s %s"%(model,sync_id))
                vals=self.import_vals(model,data)
                vals["sync_id"]=sync_id
                obj_id=get_model(model).create(vals)
            else:
                res=get_model(model).search([["sync_id","=",sync_id]])
                if not res:
                    raise Exception("Record not found: %s %s"%(model,sync_id))
                obj_id=res[0]
                get_model(model).delete([obj_id])
        elif event_type=="patch":
            res=get_model(model).search([["sync_id","=",sync_id]])
            if not res:
                raise Exception("Record not found: %s %s"%(model,sync_id))
            obj_id=res[0]
            vals=self.import_vals(model,data)
            get_model(model).write([obj_id],vals)

Account.register()
