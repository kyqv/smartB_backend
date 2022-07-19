from netforce.controller import Controller
from netforce.model import get_model
from netforce import database
from netforce import access
from netforce import config
import json

class AuthTest(Controller):
    _path="/shopee_auth_test"

    def get(self):
        print("shopee_auth_test")
        shop_idno=self.get_argument("shop_id")
        code=self.get_argument("code")
        database.set_active_db("nfo_demo_my")
        access.set_active_user(1)
        with database.Transaction():
            res=get_model("shopee.account").search([["shop_idno","=",shop_idno]])
            if not res:
                raise Exception("Shop not found: %s"%shop_idno)
            shop_id=res[0]
            shop=get_model("shopee.account").browse(shop_id)
            shop.write({"auth_code":code})
            shop.get_token_test()
            self.redirect(config.get("shopee_redirect_url2")+"/action?name=shopee_account&mode=form&active_id=%s"%shop_id)

AuthTest.register()
