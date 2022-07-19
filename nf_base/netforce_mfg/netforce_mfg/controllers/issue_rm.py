from netforce.controller import Controller
from netforce import database
from netforce.model import get_model,clear_cache
from netforce import template

class IssueRM(Controller):
    _path="/issue_rm"

    def get(self):
        db=database.get_connection()
        try:
            data={}
            html=template.render("issue_rm",data)
            self.write(html)
            db.commit()
        except Exception as e:
            db.rollback()
            import traceback
            traceback.print_exc()

    def post(self):
        db=database.get_connection()
        data={}
        try:
            data["barcode"]=self.get_argument("barcode",None)
            data["qty"]=self.get_argument("qty",None)
            barcode=data["barcode"]
            if not barcode:
                raise Exception("Missing barcode!")
            barcode=int(barcode)
            qty=data["qty"]
            if not qty:
                raise Exception("Missing qty!")
            qty=int(qty)
            res=get_model("production.component").search([["id","=",barcode]])
            if not res:
                raise Exception("Invalid barcode")
            comp_id=res[0]
            # TODO: create goods issue for that component
            db.commit()
            self.redirect("/issue_rm")
        except Exception as e:
            data["error"]="ERROR: %s"%e
            html=template.render("issue_rm",data)
            self.write(html)
            db.rollback()
            import traceback
            traceback.print_exc()

IssueRM.register()
