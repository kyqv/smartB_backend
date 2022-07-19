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
from netforce.access import get_active_user
from netforce.database import get_connection


class Contact(Model):
    _inherit = "contact"
    _fields = {
        "wishlist": fields.One2Many("ecom.wishlist", "contact_id", "Wishlist"),
        "wishlist_count": fields.Integer("Wishlist Count", function="count_wishlist"),
    }

    def count_wishlist(self, ids, context={}):
        db = get_connection()
        try:
            vals = {}
            for obj in self.browse(ids):
                contact_id = obj.id
                res = db.query("SELECT COUNT(*) FROM ecom_wishlist WHERE contact_id = %s" % contact_id)
                res = res[0]['count'] or 0
                vals[obj.id] = res
                return vals
        except:
            import traceback
            traceback.print_exc()
            db.rollback()

Contact.register()
