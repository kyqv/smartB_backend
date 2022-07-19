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
import json


class SyncModel(Model):
    _name = "sync.model"
    _fields = {
        "firebase_account_id": fields.Many2One("firebase.account","Account",required=True,on_delete="cascade"),
        "model_id": fields.Many2One("model","Model",required=True),
        "fields": fields.Text("Fields"),
        "enable_realtime": fields.Boolean("Realtime Sync"),
        "last_sync_time": fields.DateTime("Last Sync Time"),
        "filter": fields.Char("Filter"),
        "path": fields.Char("Path"),
    }

    def upload_firebase(self,ids,context={}):
        job_id=context.get("job_id")
        obj=self.browse(ids[0])
        obj.firebase_account_id.set_creds()
        m=get_model(obj.model_id.name)
        if not obj.fields:
            raise Exception("Missing fields")
        #field_paths=["sync_id"]+json.loads(obj.fields)
        field_paths=json.loads(obj.fields)
        if "sync_ids" in context:
            cond=[["id","in",context["sync_ids"]]]
        else:
            if obj.filter:
                cond=json.loads(obj.filter)
            else:
                cond=[]
        t=time.strftime("%Y-%m-%d %H:%M:%S")
        records=m.search_read_path(cond,field_paths)
        db=firebase_admin.db
        n=0
        for i,rec in enumerate(records):
            print("U"*80)
            print("rec=%s"%rec)
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,i*100/len(records),"Uploading record %s of %s."%(i+1,len(records)))
            rec=json.loads(utils.json_dumps(rec))
            """
            res=get_model("sync.record").search([["related_id","=","%s,%s"%(m._name,rec["id"])]])
            if res:
                sync_id=res[0]
                sync=get_model("sync.record").browse(sync_id)
                db.reference(sync.path).delete()
                get_model("sync.record").delete([sync_id])
            """
            table=m._table
            if obj.path:
                table=obj.path%rec
            path=table+"/"+str(rec["id"])
            #raise Exception("%s %s"%(path,rec))
            #db.reference(path).delete()
            db.reference(path).set(rec)
            """
            vals={
                "firebase_account_id": obj.firebase_account_id.id,
                "related_id": "%s,%s"%(m._name,rec["id"]),
                "path": path,
            }
            get_model("sync.record").create(vals)
            """
            n+=1
            """
            if rec["sync_id"]:
                db.reference(m._table+"/"+rec["sync_id"]).set(rec)
            else:
                ref=db.reference(m._table).push(rec)
                m.write([rec["id"]],{"sync_id":ref.key})
            """
        obj.write({"last_sync_time":t})
        return {
                "records_synced": n,
        }

    def clear_firebase(self,ids,context={}):
        obj=self.browse(ids[0])
        obj.firebase_account_id.set_creds()
        db=firebase_admin.db
        m=get_model(obj.model_id.name)
        table=m._table
        if obj.path:
            table=obj.path.split("/")[0]
        db.reference(table).delete()

    def sync_records(self,model,sync_ids,context={}):
        res=self.search([["model_id.name","=",model]])
        if not res:
            return
        obj_id=res[0]
        obj=self.browse(obj_id)
        obj.upload_firebase(context={"sync_ids":sync_ids})

SyncModel.register()
