# Copyright (c) 2012-2015 Netforce Co. Ltd.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

from netforce.model import Model, fields, get_model
from netforce import config
from netforce import database
import pkg_resources


class CreateDB(Model):
    _name = "create_db"
    _store = False
    _fields = {
        "super_password": fields.Char("Super Admin Password", required=True),
        "db_name": fields.Char("Database Name", required=True),
        "admin_password": fields.Char("Admin Password", required=True),
        "use_demo": fields.Boolean("Use demo data"),
    }

    def create_db(self, context={}):
        data = context["data"]
        if data["super_password"] != config.get("super_password"):
            raise Exception("Invalid super admin password")
        db_name = data["db_name"]
        admin_password = data["admin_password"]
        use_demo = data.get("use_demo")
        if use_demo:
            base_sql = pkg_resources.resource_string("netforce_general", "data/base_demo.sql").decode()
        else:
            base_sql = pkg_resources.resource_string("netforce_general", "data/base.sql").decode()
        print("creating db...")
        db = database.connect("template1")
        db._db.set_isolation_level(0)
        db.execute("CREATE DATABASE %s" % db_name)
        db.close()
        print("initializing db...")
        db = database.connect(db_name)
        db.execute(base_sql)
        db.execute("UPDATE base_user SET name='Admin',login='admin',password=%s WHERE id=1", admin_password)
        db.commit()
        print("done!")
        return {
            "next": {
                "name": "manage_db"
            },
            "flash": "Database created successfully",
        }

CreateDB.register()
