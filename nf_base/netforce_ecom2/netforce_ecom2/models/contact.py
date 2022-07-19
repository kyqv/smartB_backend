from netforce.model import Model,fields,get_model
from netforce import database
from netforce import utils

class Contact(Model):
    _inherit="contact"
    _fields={
        "previous_sale_products": fields.Many2Many("product","Previously Ordered Products",function="get_previous_sale_products"),
    }

    def get_previous_sale_products(self,ids,context={}):
        db=database.get_connection()
        res=db.query("SELECT contact_id,product_id,COUNT(*) FROM sale_order_line l JOIN sale_order o ON o.id=l.order_id WHERE o.contact_id IN %s GROUP BY contact_id,product_id",tuple(ids))
        contact_prods={}
        for r in res:
            contact_prods.setdefault(r.contact_id,[]).append(r.product_id)
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=contact_prods.get(obj.id,[])[:5] # XXX
        return vals

    def ecom_sign_up(self,vals,context={}):
        print("ecom_sign_up",vals,context)
        if not vals.get("first_name"):
            raise Exception("Missing first name")
        if not vals.get("last_name"):
            raise Exception("Missing last name")
        if not vals.get("email"):
            raise Exception("Missing email")
        if not vals.get("password"):
            raise Exception("Missing password")
        res=get_model("base.user").search([["email","=",vals["email"]]])
        if res:
            raise Exception("User already exists with same email")
        res=get_model("contact").search([["email","=",vals["email"]]])
        if res:
            raise Exception("Contact already exists with same email")
        cont_vals={
            "first_name": vals["first_name"],
            "last_name": vals["last_name"],
            "email": vals["email"],
            "customer":True,
        }
        contact_id=get_model("contact").create(cont_vals)
        res=get_model("profile").search([["code","=","ECOM_CUSTOMER"]])
        if not res:
            raise Exception("Customer user profile not found")
        profile_id=res[0]
        user_vals={
            "name": "%s %s"%(vals["first_name"],vals["last_name"]),
            "login": vals["email"],
            "profile_id": profile_id,
            "contact_id": contact_id,
            "password": vals["password"],
        }
        user_id=get_model("base.user").create(user_vals)
        if vals.get("address"):
            addr_vals = {
                "first_name": vals["first_name"],
                "last_name": vals["last_name"],
                "province_id": vals["province_id"],
                "type": "billing",
                "postal_code" : vals["postal_code_id"], 
                "address": vals["address"],
                "contact_id": contact_id,
                "mobile": vals["mobile"],
                "instructions_messenger" :vals['messenger'],
            }
            if vals.get("subdistrict_id"):
                subdistrict_id = vals["subdistrict_id"]
                if subdistrict_id:
                    addr_vals['subdistrict_id'] = subdistrict_id
            get_model("address").create(addr_vals)
        get_model("contact").trigger([contact_id],"ecom_sign_up")
        dbname=database.get_active_db()
        return {
            "user_id": user_id,
            "token": utils.new_token(dbname,user_id),
            "contact_id" : contact_id,
        }

    def ecom_login(self,email,password,context={}):
        print("ecom_login",email,password)
        user_id=get_model("base.user").check_password(email,password)
        if not user_id:
            raise Exception("Invalid login")
        user=get_model("base.user").browse(user_id)
        contact=user.contact_id
        if not contact:
            raise Exception("User is not a customer")
        dbname=database.get_active_db()
        return {
            "user_id": user_id,
            "token": utils.new_token(dbname,user_id),
            "contact_id": contact.id,
        }
        

Contact.register()
