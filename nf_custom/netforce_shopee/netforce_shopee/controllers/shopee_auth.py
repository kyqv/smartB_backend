from netforce.controller import Controller
from netforce.model import get_model
from netforce import database
from netforce import access
from netforce import config
import json

class Auth(Controller):
    _path="/shopee_auth"

    def get(self):
        print("shopee_auth")
        shop_idno=self.get_argument("shop_id")
        code=self.get_argument("code")
        db=self.get_argument("db")
        database.set_active_db(db)
        #database.set_active_db("nfo_demo_my") #XXX
        access.set_active_user(1)
        with database.Transaction():
            res=get_model("shopee.account").search([["shop_idno","=",shop_idno]])
            if not res:
                raise Exception("Shop not found: %s"%shop_idno)
            shop_id=res[0]
            shop=get_model("shopee.account").browse(shop_id)
            shop.write({"auth_code":code})
            shop.get_token()
            db = database.get_active_db()
            if not db:
                raise Exception("No Active DB")
            redirect_url2 = "https://%s.smartb.co" % db.replace("nfo_","").replace("_","-")
            #self.redirect(config.get("shopee_redirect_url2")+"/action?name=shopee_account&mode=form&active_id=%s"%shop_id)
            self.redirect(redirect_url2+"/action?name=shopee_account&mode=form&active_id=%s"%shop_id)

Auth.register()
