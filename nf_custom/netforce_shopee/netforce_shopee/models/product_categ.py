from netforce.model import Model, fields, get_model
from netforce import access
from netforce import config
from netforce import utils
import time
import requests
import hashlib
import hmac


class ProductCateg(Model):
    _inherit = "product.categ"
    _fields = {
        "is_shopee": fields.Boolean("Shopee Category",search=True),
        "sync_records": fields.One2Many("sync.record","related_id","Sync Records"),
        "sync_id": fields.Char("Sync ID",function="get_sync_id",function_search="search_sync_id"),
    }

    def get_sync_id(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            sync_id=None
            for sync in obj.sync_records:
                sync_id=sync.sync_id
                break
            vals[obj.id]=sync_id
        return vals

    def search_sync_id(self, clause, context={}):
        sync_id = str(clause[2])
        records = get_model("sync.record").search_browse([["related_id","ilike","product.categ,"],["sync_id","=",sync_id]])
        categ_ids = [r.related_id.id  for r in records if r.related_id]
        cond = [["id","in",categ_ids]]
        return cond

    def get_shopee_brands(self,ids,acc_id=None,context={}):
        #obj=self.browse(ids[0])
        for obj in self.browse(ids):
            if not acc_id:
                res=get_model("shopee.account").search([])
                if not res:
                    raise Exception("Shopee account not found")
                acc_id=res[0]
            if not obj.sync_id:
                raise Exception("Missing shopee ID")
            acc=get_model("shopee.account").browse(acc_id)
            if not acc.shop_idno:
                raise Exception("Missing shop ID")
            if not acc.token:
                raise Exception("Missing token")
            shop_id=int(acc.shop_idno)
            partner_id=int(config.get("shopee_partner_id"))
            partner_key=config.get("shopee_partner_key")
            timest=int(time.time())
            path="/api/v2/product/get_brand_list"
            base_string="%s%s%s%s%s"%(partner_id,path,timest,acc.token,shop_id)
            sign=hmac.new(partner_key.encode(),base_string.encode(),hashlib.sha256).hexdigest()
            #base_url="https://partner.test-stable.shopeemobile.com"
            base_url="https://partner.shopeemobile.com"
            url=base_url+path+"?partner_id=%s&timestamp=%s&sign=%s&shop_id=%s&access_token=%s"%(partner_id,timest,sign,shop_id,acc.token)
            print("url",url)
            url+="&offset=0&page_size=10&category_id=%s&status=1"%obj.sync_id
            req=requests.get(url)
            res=req.json()
            if res.get("error"):
                if context.get("skip_error"):
                    return
                raise Exception("Sync error: %s"%res)
            print("res",res)
            resp=res["response"]
            for r in resp["brand_list"]:
                vals={
                    "name": "Shopee - "+r["original_brand_name"],
                    "categs": [("set",[obj.id])],
                    "sync_records": [("create",{
                        "sync_id": r["brand_id"],
                        "account_id": "shopee.account,%s"%obj.id,
                    })],
                }
                get_model("product.brand").create(vals)

ProductCateg.register()
