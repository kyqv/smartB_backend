from netforce.model import get_model
from netforce import migration
from netforce import database

class Migration(migration.Migration):
    _name="cms.settings"
    _version="1.183.0"

    def migrate(self):
        res=get_model("cms.settings").search([["id","=",1]])
        if res:
            return
        db=database.get_connection()
        db.execute("INSERT INTO cms_settings (id,shop_name) values (1,'Test Shop')")
        #Product Category
        res=get_model("product.categ").search([["name","=","Ecommerce"]])
        if not res:
            vals={
                "name": "Ecommerce",
            }
            parent_categ_id=get_model("product.categ").create(vals)
            get_model("cms.settings").browse(1).write({"parent_categ_id":parent_categ_id})
        #Customer Contact category
        res=get_model("partner.categ").search([["name","=","Ecommerce Customer"]])
        if not res:
            vals={
                "name": "Ecommerce Customer",
            }
            contact_categ_id=get_model("partner.categ").create(vals)
            get_model("cms.settings").browse(1).write({"contact_categ_id":contact_categ_id})
        #Newsletter Contact category
        res=get_model("partner.categ").search([["name","=","Newsletter Customer"]])
        if not res:
            vals={
                "name": "Newsletter Customer",
            }
            news_categ_id=get_model("partner.categ").create(vals)
            get_model("cms.settings").browse(1).write({"news_categ_id":news_categ_id})
        #Newsletter Targetlist
        res=get_model("mkt.target.list").search([["name","=","Ecommerce"]])
        if not res:
            vals={
                "name": "Ecommerce",
            }
            target_list_id=get_model("mkt.target.list").create(vals)
            get_model("cms.settings").browse(1).write({"target_list_id":target_list_id})
        #Anonymouse User profile
        res=get_model("profile").search([["name","=","Website"]])
        if not res:
            vals={
                "name": "Website",
                "default_model_perms": "full",
            }
            profile_id=get_model("profile").create(vals)
            res=get_model("base.user").search([["login","=","website"]])
            if not res:
                vals={
                    "name": "website",
                    "login": "website",
                    "profile_id": profile_id,
                }
                user_id=get_model("base.user").create(vals)
                get_model("cms.settings").browse(1).write({"user_id":user_id})
        #Customer User profile
        res=get_model("profile").search([["name","=","Ecommerce Customer"]])
        if not res:
            vals={
                "name": "Ecommerce Customer",
                "default_model_perms": "full",
            }
            user_profile_id=get_model("profile").create(vals)
            get_model("cms.settings").browse(1).write({"user_profile_id":user_profile_id})

Migration.register()
