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

class Account(Model):
    _name = "shopee.account"
    _string = "Shopee Account"
    _fields = {
        "name": fields.Char("Shop Name",required=True,search=True),
        "shop_idno": fields.Char("Shop ID",search=True),
        "auth_code": fields.Char("Auth Code"),
        "region": fields.Char("Region"),
        "status": fields.Char("Status"),
        "token": fields.Char("Token"),
        "refresh_token": fields.Char("Refresh Token"),
        "token_expiry_time": fields.DateTime("Token Expiry Time"),
        "sale_channel_id": fields.Many2One("sale.channel","Sales Channel"),
        "sync_records": fields.One2Many("sync.record","account_id","Sync Records"),
        "pricelist_id": fields.Many2One("price.list","Price List"),
        "stock_journal_id": fields.Many2One("stock.journal","Stock Journal"),
        "contact_id": fields.Many2One("contact","Default Contact"),
        "company_id": fields.Many2One("company","Company",search=True),
        "require_invoice": fields.Boolean("Require Invoice"),
        "order_last_update_time": fields.DateTime("Shopee Order Last Update Time"),
        "payment_last_update_time": fields.DateTime("Shopee Payment Last Update Time"),
    }

    _base_url = "https://partner.shopeemobile.com"

    def generate_url(self,account_id=None,path=None,require_shop_id=True,require_token=True,context={}):
        # Check account
        if not account_id:
            raise Exception("missing account_id")
        obj = self.browse(account_id)
        if not obj:
            raise Exception("Shopee Account not found. (%s)" % account_id)

        #initialize
        base_string = ""
        url = self._base_url
        
        # general info
        if not path:
            raise Exception("missing path")
        url += path
        partner_id=int(config.get("shopee_partner_id"))
        if not partner_id:
            raise Exception("partner_id not found in config")
        timest=int(time.time())
        url += "?partner_id=%s&timestamp=%s" %(partner_id, timest)
        base_string = "%s%s%s" % (partner_id,path,timest)

        #optional info
        if require_token:
            token = obj.token
            if not token:
                raise Exception("Token not found. (%s)" % account_id)
            url += "&access_token=%s" % token
            base_string += token
        if require_shop_id:
            shop_id = int(obj.shop_idno)
            if not shop_id:
                raise Exception("Shop ID not found. (%s)" % account_id)
            url += "&shop_id=%s" % shop_id
            base_string += "%s" % shop_id
        #base_string="%s%s%s%s%s"%(partner_id,path,timest,obj.token,shop_id)

        #generate signature
        partner_key=config.get("shopee_partner_key")
        if not partner_key:
            raise Exception("partner_key not found in config")
        sign=hmac.new(partner_key.encode(),base_string.encode(),hashlib.sha256).hexdigest()
        url += "&sign=%s" % sign
        #url=base_url+path+"?partner_id=%s&timestamp=%s&sign=%s&shop_id=%s&access_token=%s"%(partner_id,timest,sign,shop_id,obj.token)
        return url

    def authorize(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.shop_idno:
            raise Exception("Shop ID not found. (%s)" % obj.id)
        path="/api/v2/shop/auth_partner"
        url = self.generate_url(account_id=obj.id, path=path, require_shop_id=False, require_token=False)

        # get redirect_url
        redirect_url=config.get("shopee_redirect_url")
        db = database.get_active_db()
        redirect_url += "?db=%s" % db
        #url=base_url+path+"?partner_id=%s&timestamp=%s&sign=%s&redirect=%s"%(partner_id,timest,sign,redirect_url)
        url += "&redirect=%s" % redirect_url

        return {
            "next": {
                "type": "url",
                "url": url,
            },
        }

    def get_token(self,ids,context={}):
        obj=self.browse(ids[0])
        path="/api/v2/auth/token/get"
        url = self.generate_url(account_id=obj.id, path=path, require_shop_id=False, require_token=False)
        print("url",url)

        # generate body
        partner_id=int(config.get("shopee_partner_id"))
        if not obj.auth_code:
            raise Exception("Missing auth code")
        shop_id=int(obj.shop_idno)
        body={"shop_id":shop_id,"code":obj.auth_code,"partner_id":partner_id}
        headers={"Content-Type":"application/json"}

        # post request and process
        req=requests.post(url,json=body,headers=headers)
        res=req.json()
        print("res",res)
        if res.get("error"):
            raise Exception(res["message"])
        token=res["access_token"]
        refresh_token=res["refresh_token"]
        expiry_time=(datetime.now() + timedelta(seconds=int(res["expire_in"]))).strftime("%Y-%m-%d %H:%M:%S")
        refresh_time=(datetime.now() + timedelta(seconds=int(res["expire_in"])) - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        obj.write({"token":token,"refresh_token":refresh_token,"token_expiry_time":expiry_time})
        task_ids = get_model("bg.task").search([["model","=","shopee.account"],["method","=","refresh_access_token"],["args","=",'{"ids":[%s]}'%obj.id],["state","=","waiting"],["date",">",datetime.now().strftime("%Y-%m-%d %H:%M:%S")]])
        if task_ids:
            print("task_ids",task_ids)
            get_model("bg.task").delete(task_ids)
        print("creating bg tasks")
        get_model("bg.task").create({
            "date": refresh_time,
            "model": "shopee.account",
            "method": "refresh_access_token",
            "args": '{"ids":[%s]}'%obj.id,
            "state": "waiting",
        })

    def refresh_access_token(self,ids,context={}):
        for obj in self.browse(ids):
            path="/api/v2/auth/access_token/get"
            url = self.generate_url(account_id=obj.id, path=path, require_shop_id=False, require_token=False)
            print("url",url)

            # generate body
            partner_id=int(config.get("shopee_partner_id"))
            if not obj.shop_idno:
                raise Exception("Missing shop ID")
            if not obj.auth_code:
                raise Exception("Missing auth code")
            shop_id=int(obj.shop_idno)
            body={"shop_id":shop_id,"refresh_token":obj.refresh_token,"partner_id":partner_id}

            headers={"Content-Type":"application/json"}
            req=requests.post(url,json=body,headers=headers)
            res=req.json()
            print("res",res)
            if res.get("error"):
                raise Exception(res["message"])
            token=res["access_token"]
            refresh_token=res["refresh_token"]
            expiry_time=(datetime.now() + timedelta(seconds=int(res["expire_in"]))).strftime("%Y-%m-%d %H:%M:%S")
            refresh_time=(datetime.now() + timedelta(seconds=int(res["expire_in"])) - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
            obj.write({"token":token,"refresh_token":refresh_token,"token_expiry_time":expiry_time})
            print("finish_write")
            task_ids = get_model("bg.task").search([["model","=","shopee.account"],["method","=","refresh_access_token"],["args","=",'{"ids":[%s]}'%obj.id],["state","=","waiting"]])
            if task_ids:
                print("task_ids",task_ids)
                get_model("bg.task").delete(task_ids)
            print("creating bg tasks")
            get_model("bg.task").create({
                "date": refresh_time,
                "model": "shopee.account",
                "method": "refresh_access_token",
                "args": '{"ids":[%s]}'%obj.id,
                "state": "waiting",
            })
        return {
            "alert":"Access Tokens Refreshed Successfully"
        }

    def get_info(self,ids,context={}):
        obj=self.browse(ids[0])
        path="/api/v2/shop/get_shop_info"
        url = self.generate_url(account_id=obj.id, path=path)
        print("url",url)
        req=requests.get(url)
        res=req.json()
        print("res",res)
        vals={
            "name": res["shop_name"],
            "region": res["region"],
            "status": res["status"],
        }
        obj.write(vals)

    def upload_categs(self,ids,context={}):
        obj=self.browse(ids[0])
        path="/api/v2/shop_category/add_shop_category"
        url = self.generate_url(account_id=obj.id, path=path)
        print("url",url)
        db=database.get_connection()
        for categ in get_model("product.categ").search_browse([]):
            if categ.shopee_id:
                continue
            data={
                "name": categ.name,
            }
            #data["name"]="OA_V2_1"
            req=requests.post(url,json=data)
            res=req.json()
            if res.get("error"):
                raise Exception("Sync error: %s"%res)
            print("res",res)
            resp=res["response"]
            categ.write({"shopee_id":resp["shop_category_id"]})
            db.commit()

    def upload_image(self,ids,fname,context={}):
        obj=self.browse(ids[0])
        path="/api/v2/media_space/upload_image"
        url = self.generate_url(account_id=obj.id, path=path)
        path=utils.get_file_path(fname)
        print("path",path)
        f=open(path,"rb")
        files={"image":f}
        req=requests.post(url,files=files)
        res=req.json()
        if res.get("error"):
            raise Exception("Sync error: %s"%res)
        resp=res["response"]
        img_id=resp["image_info"]["image_id"]
        return img_id

    def upload_products(self,ids,context={}):
        obj=self.browse(ids[0])
        for prod in get_model("product").search_browse([["sale_channels.id","=",obj.sale_channel_id.id]]):
            #Chin Added for multiple account
            sync_id = None
            for r in prod.sync_records or []:
                if r.account_id.id == obj.id:
                    sync_id = r.sync_id
                    break
            #if prod.sync_records:
            if sync_id:
                obj.update_product_shopee(prod.id,sync_id)
            else:
                obj.add_product_shopee(prod.id)

    def add_product_shopee(self,ids,prod_id,context={}):
        obj=self.browse(ids[0])
        path="/api/v2/product/add_item"
        url = self.generate_url(account_id=obj.id, path=path)
        print("url",url)
        db=database.get_connection()
        prod=get_model("product").browse(prod_id,context={"pricelist_id":obj.pricelist_id.id})
        prod_shopee_details=get_model("product.shopee.details").search_browse([["product_id","=",prod_id],["account_id","=",obj.id]])
        prod2=prod_shopee_details[0] if len(prod_shopee_details) else None
        print("add product %s"%prod.name)
        name = prod2.name if (prod2 and prod2.name) else prod.name
        description = prod2.description if (prod2 and prod2.description) else prod.description
        if not prod.customer_price:
            raise Exception("Missing sales price for product %s"%prod.code)
        categ=prod2.categ_id if (prod2 and prod2.categ_id) else prod.categ_id
        if not categ:
            raise Exception("Missing category for product %s"%prod.code)
        if not prod.image:
            raise Exception("Missing image for product %s"%prod.code)
        img_id=obj.upload_image(prod.image)
        img_ids=[img_id]
        if not categ.sync_id:
            raise Exception("Missing category sync ID")
        if not prod.ship_methods:
            raise Exception("Missing shipping methods for product %s"%prod.code)
        brand=prod2.brand_id if (prod2 and prod2.brand_id) else prod.brand_id
        if not brand:
            raise Exception("Missing brand")
        if not brand.sync_id:
            raise Exception("Missing brand sync ID")
        ship_methods = prod2.ship_methods if (prod2 and prod2.ship_methods and len(prod2.ship_methods)) else prod.ship_methods
        if not prod.weight:
            raise Exception("Missing weight")
        if not prod.height:
            raise Exception("Missing height")
        if not prod.length:
            raise Exception("Missing length")
        if not prod.width:
            raise Exception("Missing width")
        data={
            "original_price": float(prod.customer_price),
            "description": description or "/",
            "item_name": name,
            "normal_stock": int(prod.stock_qty),
            "weight": float(prod.weight),
            "logistic_info": [],
            "category_id": int(categ.sync_id),
            "image": {
                "image_id_list": img_ids,
            },
            "logistic_info": [{
                "logistic_id": int(m.sync_id),
                "enabled": True,
            } for m in ship_methods if m.sync_id],
            "dimension": {
                "package_height": int(prod.height),
                "package_length": int(prod.length),
                "package_width": int(prod.width),
            },
            "pre_order": {
                "is_pre_order": False,
            },
            "brand": {
                "brand_id": int(brand.sync_id),
                "original_brand_name": brand.name,
            },
        }
        print("data",data)
        req=requests.post(url,json=data)
        res=req.json()
        if res.get("error"):
            raise Exception("Sync error: %s"%res)
        resp=res["response"]
        sync_id=resp["item_id"]
        vals={
            "sync_id": sync_id,
            "account_id": "shopee.account,%s"%obj.id,
            "related_id": "product,%s"%prod.id,
        }
        get_model("sync.record").create(vals)
        db.commit()

    def update_product_shopee(self,ids,prod_id,sync_id,context={}):
        obj=self.browse(ids[0])
        path="/api/v2/product/update_item"
        url = self.generate_url(account_id=obj.id, path=path)
        print("url",url)
        db=database.get_connection()
        prod=get_model("product").browse(prod_id,context={"pricelist_id":obj.pricelist_id.id})
        #sync_id=int(prod.sync_records[0].sync_id)
        print("update product %s"%prod.name)
        if not prod.customer_price:
            raise Exception("Missing sales price for product %s"%prod.code)
        categ=prod.categ_id
        if not categ:
            raise Exception("Missing category for product %s"%prod.code)
        if not prod.image:
            raise Exception("Missing image for product %s"%prod.code)
        img_id=obj.upload_image(prod.image)
        img_ids=[img_id]
        if not categ.sync_id:
            raise Exception("Missing category sync ID")
        if not prod.ship_methods:
            raise Exception("Missing shipping methods for product %s"%prod.code)
        brand=prod.brand_id
        if not brand:
            raise Exception("Missing brand")
        if not brand.sync_id:
            raise Exception("Missing brand sync ID")
        if not prod.weight:
            raise Exception("Missing weight")
        if not prod.height:
            raise Exception("Missing height")
        if not prod.length:
            raise Exception("Missing length")
        if not prod.width:
            raise Exception("Missing width")
        data={
            "item_id": sync_id,
            "original_price": float(prod.customer_price),
            "description": prod.description or "/",
            "item_name": prod.name,
            "normal_stock": int(prod.stock_qty),
            "weight": float(prod.weight),
            "logistic_info": [],
            "category_id": int(categ.sync_id),
            "image": {
                "image_id_list": img_ids,
            },
            "logistic_info": [{
                "logistic_id": int(m.sync_id),
                "enabled": True,
            } for m in prod.ship_methods if m.sync_id],
            "dimension": {
                "package_height": int(prod.height),
                "package_length": int(prod.length),
                "package_width": int(prod.width),
            },
            "pre_order": {
                "is_pre_order": False,
            },
            "brand": {
                "brand_id": int(brand.sync_id),
                "original_brand_name": brand.name,
            },
        }
        print("data",data)
        req=requests.post(url,json=data)
        res=req.json()
        if res.get("error"):
            raise Exception("Sync error: %s"%res)
        resp=res["response"]
        db.commit()

    def get_products(self,ids,context={}):
        obj = self.browse(ids[0])
        path="/api/v2/product/get_item_list"
        url = self.generate_url(account_id=obj.id, path=path)
        print("url",url)
        item_status = context.get("item_status") or "NORMAL"
        page_size = context.get("page_size") or 50
        url += "&item_status=%s&page_size=%s" % (item_status,page_size)
        update_time_from = context.get("update_time_from") or None
        if update_time_from:
            url += "&update_time_from=%s" % update_time_from
        update_time_to = context.get("update_time_to") or None
        if update_time_to:
            url += "&update_time_to=%s" % update_time_to
        print("url",url)

        offset = 0
        limit = context.get("limit") or 10000
        loop_limit = 1000
        item_ids = []
        total = 0
        i = 0
        job_id = context.get("job_id")
        while len(item_ids) <= limit and i < loop_limit:
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,50,"Step 1: Reading Products from Shopee: %s found."%(total))
            req_url = url + "&offset=%s" % offset
            print("req_url",req_url)
            req=requests.get(req_url)
            res=req.json()
            if res.get("error"):
                raise Exception("Sync error: %s"%res)
            print("res",res)
            resp=res["response"]
            item_ids.extend([item["item_id"] for item in resp["item"]])
            total += len(item_ids)
            if not resp["has_next_page"]:
                break
            else:
                offset = resp["next_offset"]
            i += 1
        db = database.get_connection()
        j = 0
        while j < len(item_ids):
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,50+j/len(item_ids)*50,"Step 2: Writing %s of %s Products to Database"%(j,len(item_ids)))
            is_last = j + 50 > len(item_ids)
            if is_last:
                self.get_products_info(obj.id, item_ids[j:], context=context)
            else:
                self.get_products_info(obj.id, item_ids[j:j+50], context=context)
            db.commit()
            j += 50

    def get_products_info(self, account_id, item_ids, context={}):
        if len(item_ids) > 50:
            self.get_products_info(account_id, item_ids[0:50], context=context)
            self.get_products_info(account_id, item_ids[50:],context=context)
        settings = get_model("shopee.settings").browse(1)
        if not settings:
            raise Exception("Shopee Settings not found")
        path="/api/v2/product/get_item_base_info"
        url = self.generate_url(account_id=account_id,path=path)
        url += "&item_id_list=%s" % ",".join([str(k) for k in item_ids])
        print("url",url)
        req = requests.get(url)
        res = req.json()
        if res.get("error"):
            raise Exception("Sync error: %s"%res)
        resp = res["response"]
        print("resp",resp)
        for item in resp["item_list"]:
            vals = {
                "account_id": account_id,
                "item_name": item["item_name"],
                "item_sku": item["item_sku"],
                "sync_id": item["item_id"],
                "description": item["description"],
                "condition": item["condition"],
                "item_status": item["item_status"],
                "has_model": item["has_model"],
            }
            vals["shopee_create_time"] = datetime.fromtimestamp(item["create_time"]).strftime("%Y-%m-%d %H:%M:%S") 
            vals["shopee_update_time"] = datetime.fromtimestamp(item["update_time"]).strftime("%Y-%m-%d %H:%M:%S") 
            if not item["has_model"]:
                if item.get("stock_info"):
                    for si in item["stock_info"]:
                        if si["stock_type"] == 2:
                            vals["normal_stock"] = si["normal_stock"]
                if item.get("price_info"):
                    vals["current_price"] = item["price_info"][0]["current_price"]

            if item["category_id"]:
                categs = get_model("shopee.product.categ").search([["sync_id","=",str(item["category_id"])]])
                vals["category_id"] = categs[0] if categs else None
            prods = get_model("shopee.product").search([["account_id","=",str(account_id)],["sync_id","=",str(item["item_id"])]])
            if not prods:
                prod_id = get_model("shopee.product").create(vals)
            else:
                prod_id = prods[0]
                get_model("shopee.product").write([prod_id],vals)
            prod = get_model("shopee.product").browse(prod_id)
            if item["has_model"]:
                prod.get_model_list()
            prod.map_product()
    
    def get_products_info_old(self, account_id, item_ids, context={}):
        if len(item_ids) > 50:
            self.get_products_info(item_ids[0:50])
            self.get_products_info(item_ids[50:])
        settings = get_model("shopee.settings").browse(1)
        if not settings:
            raise Exception("Shopee Settings not found")
        path="/api/v2/product/get_item_base_info"
        url = self.generate_url(account_id=account_id,path=path)
        url += "&item_id_list=%s" % ",".join([str(k) for k in item_ids])
        print("url",url)
        req = requests.get(url)
        res = req.json()
        if res.get("error"):
            raise Exception("Sync error: %s"%res)
        resp = res["response"]
        print("resp",resp)
        for item in resp["item_list"]:
            vals = get_model("product").default_get()
            if vals.get("company_id"):
                vals["company_id"] = vals["company_id"][0]
            if not vals.get("type"):
                vals["type"] = "stock"
            if settings.default_uom_id:
                vals["uom_id"] = settings.default_uom_id.id
            #vals={}
            if item["item_sku"]:
                vals["code"] = item["item_sku"]
            vals["name"] = item["item_name"]
            if item["category_id"]:
                categs = get_model("product.categ").search([["sync_id","=",item["category_id"]]])
                vals["categ_id"] = categs[0] if categs else None
            vals["description"] = item["description"]
            vals["weight"] = item["weight"]
            # Add iamage here XXX
            if item["brand"]:
                brands= get_model("product.brand").search([["sync_id","=",item["brand"]["brand_id"]]])
                vals["brand_id"] = brands[0] if brands else None
            if item["logistic_info"]:
                logistic_ids = [l["logistic_id"] for l in item["logistic_info"] if l.get("enabled") and l["enabled"]==True]
                method_ids = []
                for lid in logistic_ids:
                    methods = get_model("ship.method").search([["sync_id","=",lid]])
                    if methods:
                        method_ids.append(methods[0])
                vals["ship_methods"] = [["set",method_ids]]
            vals["sync_records"]= [("create",{
                "sync_id": item["item_id"],
                "account_id": "shopee.account,%s"%account_id,
                })]
            prod_sync = get_model("sync.record").search_browse([
                ["account_id","=","shopee.account,%s"%account_id],
                ["related_id","like","product"],
                ["sync_id","=",str(item["item_id"])
                ]])
            prod = None
            if prod_sync:
                prod = prod_sync[0].related_id
                print("prod_sync found: %s"%prod)
            elif item["item_sku"]:
                prods = get_model("product").search_browse([["code","=",item["item_sku"]]])
                prod = prods[0] if prods else None
                print("prod with code found: %s"%prod)
            if prod:
                prod.write(vals)
            else:
                get_model("product").create(vals)

    def get_logis(self,ids,context={}):
        obj=self.browse(ids[0])
        path="/api/v2/logistics/get_channel_list"
        url = self.generate_url(account_id=obj.id, path=path)
        print("url",url)
        #data["name"]="OA_V2_1"
        req=requests.get(url)
        res=req.json()
        if res.get("error"):
            raise Exception("Sync error: %s"%res)
        print("res",res)
        resp=res["response"]
        for r in resp["logistics_channel_list"]:
            method_name = "Shopee - "+r["logistics_channel_name"]
            methods = get_model("ship.method").search_browse([["name","=",method_name]])
            if len(methods) == 0:
                vals={
                    #"name": "Shopee - "+r["logistics_channel_name"],
                    "name": method_name,
                    "sync_records": [("create",{
                        "sync_id": r["logistics_channel_id"],
                        "account_id": "shopee.account,%s"%obj.id,
                    })],
                }
                get_model("ship.method").create(vals)
            else:
                method = methods[0]
                
    def get_categ(self,ids,context={}):
        for acc_id in ids:
            context["account_id"] = acc_id
            get_model("shopee.product.categ").get_categ(context=context)

    def get_shop_categ(self,ids,context={}):
        obj=self.browse(ids[0])
        path="/api/v2/shop_category/get_shop_category_list"
        url = self.generate_url(account_id=obj.id, path=path)
        url+="&page_size=20"
        url+="&page_no=1"
        print("url",url)
        #data["name"]="OA_V2_1"
        req=requests.get(url)
        res=req.json()
        if res.get("error"):
            raise Exception("Sync error: %s"%res)
        print("res",res)
        resp=res["response"]
        db=database.get_connection()
        for r in resp["shop_categorys"]:
            vals={
                "name": "Shopee Shop Categ - "+r["name"],
                "sync_records": [("create",{
                    "sync_id": r["shop_category_id"],
                    "account_id": "shopee.account,%s"%obj.id,
                })],
            }
            print("vals",vals)
            get_model("product.categ").create(vals)
            db.commit()

    def get_brands(self,ids,context={}):
        obj=self.browse(ids[0])
        categ_sync=get_model("sync.record").search_browse([["account_id","=","shopee.account,%s"%obj.id],["related_id","like","product.categ"]])
        job_id = context.get("job_id")
        i=0
        for c in categ_sync:
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,i/len(categ_sync)*100,"Getting brands for %s of %s Product Categories."%(i+1,len(categ_sync)))
            i += 1
            categ = c.related_id
            print("inspect categ ==>")
            print(categ)
            categ.get_shopee_brands(acc_id=obj.id,context={"skip_error":True})


    def get_orders(self,ids,context={}):
        print("get_orders")
        obj=self.browse(ids[0])
        path="/api/v2/order/get_order_list"
        url = self.generate_url(account_id=obj.id, path=path)
        url+="&time_range_field=update_time"
        settings = get_model("shopee.settings").search_browse([])[0]
        if not obj.order_last_update_time:
            raise Exception("Missing Shopee Order Last Update Time. Please choose a Datetime in Shopee Account")
        last_update_time = datetime.strptime(obj.order_last_update_time,"%Y-%m-%d %H:%M:%S")
        print("Last Update Time: %s" % last_update_time)
        order_nos = []
        first_page = True
        cursor = None
        current_time = datetime.now()
        orders_found = 0
        while len(order_nos) < 10000:
            time_to = min(last_update_time + timedelta(days=15),current_time)
            url2 = url + "&time_from=%s"%int(last_update_time.timestamp())
            url2 += "&time_to=%s"%int(time_to.timestamp())
            if cursor:
                url2 += "&cursor=%s"%cursor
            url2 += "&page_size=%s" % (context.get("page_size") or "100")
            print("url2",url2)
            req=requests.get(url2)
            res=req.json()
            if res.get("error"):
                raise Exception("Sync error: %s"%res)
            print("res",res)
            resp=res["response"]
            orders_found += len(resp["order_list"])
            for r in resp["order_list"]:
                order_nos.append(r["order_sn"])
            if resp["more"]:
                cursor = resp["next_cursor"]
            elif time_to == current_time:
                break
            else:
                cursor = None
                first_page = True
                last_update_time = time_to

        #old_order_nos=set()
        #for sync in get_model("sync.record").search_browse([["account_id","=","shopee.account,%s"%obj.id],["related_id","like","sale.order"]]):
        #    old_order_nos.add(sync.sync_id)
        job_id = context.get("job_id")
        i = 0
        for order_no in order_nos:
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,i/len(order_nos)*100,"Updating Orders: %s of %s."%(i,len(order_nos)))
            #if order_no in old_order_nos:
            #    continue
            self.get_order(ids,order_no)
            i += 1
        obj.write({"order_last_update_time":time_to.strftime("%Y-%m-%d %H:%M:%S")})

    def get_order(self,ids,order_no,context={}):
        print("get_order",order_no)
        obj=self.browse(ids[0])
        path="/api/v2/order/get_order_detail"
        url = self.generate_url(account_id=obj.id, path=path)
        url+="&order_sn_list=%s"%order_no
        #url+="&response_optional_fields=buyer_username,buyer_user_id,item_list,recipient_address,create_time.ship_by_date,note"
        url+="&response_optional_fields=buyer_user_id,buyer_username,estimated_shipping_fee,recipient_address,actual_shipping_fee ,goods_to_declare,note,note_update_time,item_list,pay_time,dropshipper,dropshipper_phone,split_up,buyer_cancel_reason,cancel_by,cancel_reason,actual_shipping_fee_confirmed,buyer_cpf_id,fulfillment_flag,pickup_done_time,package_list,shipping_carrier,payment_method,total_amount,buyer_username,invoice_data, checkout_shipping_carrier, reverse_shipping_fee"
        print("url",url)
        #data["name"]="OA_V2_1"
        req=requests.get(url)
        res=req.json()
        if res.get("error"):
            raise Exception("Sync error: %s"%res)
        print("res",res)
        resp=res["response"]
        settings = get_model("shopee.settings").browse(1)
        for o in resp["order_list"]:
            orders = get_model("shopee.order").search_browse([["order_sn","=",str(o["order_sn"])]])
            if not orders:
                order_id=get_model("shopee.order").create_order(obj.id,o,context)
            else:
                order_id=orders[0].id
                orders[0].update_order(obj.id,o,context)
            #res=get_model("sale.order").search([["sync_records.sync_id","=",str(o["order_sn"])]])
            #order_id=res[0] if res else None
            #order_id=None
            #cont_id=None
            #sale_id=None
            #if shopee_settings.include_contact:
            #    cont_id = get_model("contact").get_shopee_contact(obj.id,o,context)
            #    context["cont_id"] = cont_id
            #if shopee_settings.include_sale:
            #    sale_id = get_model("sale.order").get_shopee_order(obj.id,o,context)
            #    context["sale_id"] = sale_id
            #if shopee_settings.include_inventory:
            #    pick_id = get_model("stock.picking").get_shopee_order(obj.id,o,context)
        return order_id


    def get_payments_old(self,ids,context={}):
        print("get_payments")
        obj=self.browse(ids[0])
        path="/api/v2/payment/get_escrow_list"
        url = self.generate_url(account_id=obj.id, path=path)
        url+="&releast_time_from=%s"%int((datetime.now()-timedelta(days=10)).timestamp())
        url+="&release_time_to=%s"%int((datetime.now()-timedelta(days=0)).timestamp())
        url+="&page_size=100"
        url+="&page_no=1"
        print("url",url)
        #data["name"]="OA_V2_1"
        req=requests.get(url)
        res=req.json()
        if res.get("error"):
            raise Exception("Sync error: %s"%res)
        print("res",res)
        resp=res["response"]
        for es in resp["escrow_list"]:
            res=get_model("sync.record").search([["sync_id","=",str(es["order_sn"])]])
            if not res:
                raise Exception("Product not found: %s"%es["order_sn"])
            sync_id=res[0]
            sync=get_model("sync.record").browse(sync_id)
            order=sync.related_id
            if not order.invoices:
                raise Exception("Invoice not found for sales order: %s"%order.number)
            inv=order.invoices[0]
            if inv.payments:
                continue
            vals={
                "type": "in",
                "pay_type": "invoice",
                "contact_id": order.contact_id.id,
                "date": datetime.fromtimestamp(es["escrow_release_time"]).strftime("%Y-%m-%d"),
                "memo": "Shopee",
                "lines": [("create",{
                    "invoice_id": inv.id,
                    "amount": es["payout_amount"],
                })],
            }
            pmt_id=get_model("account.payment").create(vals)

Account.register()
