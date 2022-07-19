from netforce.model import Model, fields, get_model
from netforce import config
from netforce import utils
from netforce import database
from netforce import tasks
from netforce import access
import requests
import hashlib
import hmac
from datetime import *
import time

class Category(Model):
    _name = "shopee.product.categ"
    _string = "Shopee Product Category"
    _fields = {
        "sync_id": fields.Char("Sync ID"), #XXX category_id
        "parent_id": fields.Many2One("shopee.product.categ","Parent Category",search=True), #parent_category_id = parent_id.sync_id
        "original_category_name": fields.Char("Original Category Name", search=True),
        "display_category_name": fields.Char("Display Category Name", search=True),
        "has_children": fields.Boolean("Has Children", search=True),
    }

    _MAX_DEPTH = 20

    def name_get(self, ids, context={}):
        print("shopee.product.categ.name_get",ids)
        vals = []
        for obj in self.browse(ids):
            name = obj.display_category_name or obj.original_category_name
            parent_id = obj.parent_id
            depth = 0
            while depth < self._MAX_DEPTH:
                if not parent_id:
                    break
                name = "%s=>%s" % (parent_id.display_category_name or parent_id.original_category_name, name)
                parent_id = parent_id.parent_id 
                depth += 1
            vals.append((obj.id, name, obj.image))
        return vals 

    def get_categ(self,context={}):
        print("shopee.product.categ.get_categ")
        if context.get("account_id"):
            acc = get_model("shopee.account").browse(context["account_id"])
        else:
            acc = get_model("shopee.account").search_browse([])[0]
        path="/api/v2/product/get_category"
        url = get_model("shopee.account").generate_url(account_id=acc.id, path=path)
        print("url",url)
        req=requests.get(url)
        res=req.json()
        if res.get("error"):
            raise Exception("Sync error: %s"%res)
        resp=res["response"]
        db=database.get_connection()
        job_id = context.get("job_id")
        i = 0
        for r in resp["category_list"]:           
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,i*100/len(resp["category_list"]),"Writing record %s of %s to database."%(i+1,len(resp["category_list"])))
            parent_id = None
            if r["parent_category_id"]:
                parents = get_model("shopee.product.categ").search([["sync_id","=",str(r["parent_category_id"])]])
                parent_id = parents[0] if len(parents) > 0 else None
            vals={
                "parent_id": parent_id,
                "original_category_name": r["original_category_name"],
                "display_category_name": r["display_category_name"],
                "sync_id": r["category_id"],
                "has_children": r["has_children"],
            }
            #print("vals",vals)
            categs = get_model("shopee.product.categ").search([["sync_id","=",str(r["category_id"])]])
            if len(categs) == 0:
                get_model("shopee.product.categ").create(vals)
            else:
                get_model("shopee.product.categ").write(categs,vals)
            db.commit()
            i+=1

Category.register()
