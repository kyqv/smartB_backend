from netforce.model import Model,fields,get_model
from netforce import utils
from netforce import database

class EcomInterface(Model):
    _name="ecom2.interface"
    _store=False

    def sign_up(self,vals,context={}):
        #print("EcomInterface.sign_up",vals,context)
        if not vals.get("username"):
            raise Exception("Missing username")
        if not vals.get("password"):
            raise Exception("Missing password")
        #if not vals.get("first_name"):
        #    raise Exception("Missing first name")
        #if not vals.get("last_name"):
        #    raise Exception("Missing last name")
        res=get_model("base.user").search([["login","=",vals["username"]]])
        if res:
            raise Exception("User already exists with same username")
        #res=get_model("contact").search([["email","=",vals["email"]]])
        #if res:
        #    raise Exception("Contact already exists with same email")
        cont_vals={
            "first_name": vals.get("first_name"),
            "last_name": vals.get("last_name") or vals.get("full_name"),
            "email": vals.get("email"),
            "customer":True,
            "mobile": vals.get("mobile"),
            "id_card_no": vals.get("id_card"),
            "line_account": vals.get("line_account"),
            "facebook_account": vals.get("facebook_account"),
        }
        if vals.get("ref_id_card"):
            res=get_model("contact").search([["id_card_no","=",vals["ref_id_card"]]])
            if not res:
                raise Exception("Customer not found with ID card: %s"%vals["ref_id_card"])
            refer_id=res[0]
            cont_vals["refer_id"]=refer_id
            cont_vals["commission_parent_id"]=refer_id
        if vals.get("refer_id"):
            cont_vals["refer_id"]=vals["refer_id"]
        contact_id=get_model("contact").create(cont_vals)
        res=get_model("profile").search([["code","=","ECOM_CUSTOMER"]])
        if not res:
            raise Exception("Customer user profile not found")
        profile_id=res[0]
        user_vals={
            "name": "%s %s"%(vals["first_name"],vals["last_name"]) if vals.get("first_name") else vals.get("full_name"),
            "login": vals["username"],
            "profile_id": profile_id,
            "contact_id": contact_id,
            "password": vals["password"],
        }
        user_id=get_model("base.user").create(user_vals)
        if vals.get("address"):
            addr_vals = {
                "first_name": vals.get("first_name"),
                "last_name": vals.get("last_name"),
                "province_id": vals.get("province_id"),
                "type": "billing",
                "postal_code" : vals.get("postal_code_id"), 
                "address": vals.get("address"),
                "contact_id": contact_id,
                "mobile": vals.get("mobile"),
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

    def login(self,email,password,context={}):
        #print("EcomInterface.login",email,password)
        user_id=get_model("base.user").check_password(email,password)
        if not user_id:
            raise Exception("Invalid login")
        user=get_model("base.user").browse(user_id)
        contact=user.contact_id
        dbname=database.get_active_db()
        return {
            "user_id": user_id,
            "token": utils.new_token(dbname,user_id),
            "contact_id": contact.id,
        }

    def checkEmail(self,login,context={}):
        print("EcomInterface.CheckEmail",login)
        res = get_model("base.user").search_browse([['login','=',login]])
        if res:
            id = res[0].id
            reset_code = res.password_reset(id)
            vals = {
            "body":"Please click the link to reset the code: http://localhost/reset_password?code=%s"%reset_code,
            "from_addr":"demo@netforce.com",
            "subject" : "Reset Code",
            "type": "out",
            "state":"to_send",
            "to_addrs":login,
            "mailbox_id":1,
            }
            get_model('email.message').create(vals)            
        else: 
            raise Exception("Email Not Found");
        return 

    def check_reset_code_exist(self,reset_code,context={}):
        print("EcomInterface.checkResetCodeExist",reset_code)
        res = get_model("base.user").search([["password_reset_code","=",reset_code]])
        if not res:
            raise Exception("Invalid Code")

    def set_new_password(self,reset_code,new_password,context={}):
        print("EcomInterface.set_new_password",reset_code,new_password) 
        res = get_model("base.user").search([["password_reset_code","=",reset_code]])
        if not res:
            raise Exception("Can not find user")
        user = get_model("base.user").browse(res[0])
        user.write({"password": new_password})

    def add_request_product_groups(self,contact_id,prod_group_id,context={}):
        print("Ecom2Interface.add_request_product_group",contact_id,prod_group_id)
        #contact_id=context.get("contact_id")
        contact=get_model("contact").browse(contact_id)
        if len(contact.request_product_groups) >=3:
            raise Exception("Maximum 3 ")
        update = True
        for group in contact.request_product_groups:
            print("group",group.id)
            if group.id == prod_group_id:
                update = False
        if update:
            contact.write({"request_product_groups":[("add",[prod_group_id])]})

    def remove_request_product_groups(self,contact_id,prod_group_id,context={}):
        print("Ecom2Interface.remove_request_product_group",contact_id,prod_group_id)
        #contact_id=context.get("contact_id")
        contact=get_model("contact").browse(contact_id)
        contact.write({"request_product_groups":[("remove",[prod_group_id])]})

    def add_exclude_product_groups(self,contact_id,prod_group_id,context={}):
        print("Ecom2Interface.exclude_product_groups",contact_id,prod_group_id)
        #contact_id=context.get("contact_id")
        contact=get_model("contact").browse(contact_id)
        if len(contact.exclude_product_groups) >=3:
            raise Exception("Maximum 3 ")
        update = True
        for group in contact.exclude_product_groups:
            print("group",group.id)
            if group.id == prod_group_id:
                update = False
        if update:
            contact.write({"exclude_product_groups":[("add",[prod_group_id])]})

    def remove_exclude_product_groups(self,contact_id,prod_group_id,context={}):
        print("Ecom2Interface.remove_request_product_group",contact_id,prod_group_id)
        #contact_id=context.get("contact_id")
        contact=get_model("contact").browse(contact_id)
        contact.write({"exclude_product_groups":[("remove",[prod_group_id])]})

EcomInterface.register()
