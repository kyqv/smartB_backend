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

from netforce.model import Model, fields, get_model, update_db
from netforce import config
from netforce import database
from netforce.migration import apply_migrations
import pkg_resources
from netforce.utils import get_db_version


class UpgradeDB(Model):
    _name = "upgrade_db"
    _store = False
    _fields = {
        "super_password": fields.Char("Super Admin Password", required=True),
        "dbname": fields.Selection([], "Database Name", required=True),
    }

    def get_databases(self, context={}):
        db_list = sorted(database.list_databases())
        if config.get("sub_server"):
            request = context["request"]
            host = request.host
            i = host.find(".my.netforce.com")
            if i == -1:
                raise Exception("Invalid host")
            db_name = host[:i].replace("-", "_")
            db_list = [db_name]
        elif config.get("database"):
            db_list = [config.get("database")]
        return [(x, x) for x in db_list]

    def upgrade_db(self, context={}):
        data = context["data"]
        if data["super_password"] != config.get("super_password"):
            raise Exception("Invalid super admin password")
        dbname = data["dbname"]
        database.set_active_db(dbname)
        from_version = get_db_version()
        update_db(force=True)
        apply_migrations(from_version=from_version)
        return {
            "next": {
                "name": "manage_db"
            },
            "flash": "Database upgrade successfully",
        }

UpgradeDB.register()
