from netforce.model import get_model
from netforce import migration
from netforce.database import get_connection

class Migration(migration.Migration):
    _name="product.prod_attr"
    _version="2.12.0"

    def migrate(self):
        db = get_connection()
        res_db = db.query('''SELECT code FROM product_custom_option GROUP By code HAVING count(code) > 1;''')
        #Merge Duplicate Cust opt
        for code in res_db:
            res = get_model("product.custom.option").search_browse([["code","=",code['code']]])
            for option in res[1:]:
                for value in option.values:
                    value.write({"cust_opt_id": res[0].id})
                option.delete()
        #Copy Custom Option to Attribute
        for obj in get_model("product.custom.option").search_browse([]):
            res = get_model("product.attribute").search_browse([["name","=",obj.name]])
            if not res:
                attr_vals={
                    "name": obj.name,
                    "values": [],
                }
                for value in obj.values:
                    values_vals={
                        "name": value.name,
                        "code": value.code,
                        "sequence": 0,
                    }
                    attr_vals['values'].append(("create",values_vals))
                get_model("product.attribute").create(attr_vals)
                print("Create New Attr :%s"%obj.name)
            else:
                attr = res[0]
                for value in obj.values:
                    res = get_model("product.attribute.val").search([["code","=",value.code],["attribute_id","=",attr.id]])
                    if not res:
                        values_vals={
                            "attribute_id": attr.id,
                            "name": value.name,
                            "code": value.code,
                            "sequence": 0,
                        }
                        get_model("product.attribute.val").create(values_vals)
                        print("Existing Attr :%s add new value :%s"%(attr.name,value.name))
        #Copy Attribute Value text > select
        for obj in get_model("product").search_browse([]):
            if obj.type == 'stock' and obj.parent_id is not None:
                for attr in obj.attributes:
                    if attr.attribute_id.name.startswith("_CUST_OPT_"):
                        cust_code =  attr.attribute_id.name.replace("_CUST_OPT_","")
                        res = get_model("product.custom.option").search_browse([["code","=",cust_code]])
                        if res:
                            cust = res[0]
                            attr_id = get_model("product.attribute").search([["name","=",cust.name]])[0]
                            print("Product Id: %s"%obj.id)
                            print("Attr value : %s"%attr.value)
                            print("Attribute Id : %s"%attr_id)
                            res2 = get_model("product.attribute.val").search([["code","=",attr.value],["attribute_id","=",attr_id]])
                            if res2:
                                value_id = res2[0]
                                attr.write({"attribute_id": attr_id,"value_id":value_id})

Migration.register()
