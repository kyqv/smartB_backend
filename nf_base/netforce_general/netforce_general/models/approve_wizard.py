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
from netforce.access import get_active_company, get_active_user, set_active_user
from netforce import utils
from netforce import database


class ApproveWizard(Model):
    _name = "approve.wizard"
    _transient = True
    _fields = {
        "approve_model": fields.Char("Approve Model"),
        "approve_id": fields.Integer("Approve ID"),
        "approve_method": fields.Char("Approve Method"),
        "approver_id": fields.Many2One("base.user", "Approver"),
        "pin_code": fields.Char("PIN Code"),
    }
    _defaults = {
        "approve_model": lambda self, ctx: ctx.get("approve_model"),
        "approve_id": lambda self, ctx: int(ctx["refer_id"]),
        "approve_method": lambda self, ctx: ctx.get("approve_method"),
    }

    def approve(self, ids, context={}):
        print("ApproveWizard.approve", ids)
        obj = self.browse(ids)[0]
        pin_code = obj.pin_code
        obj.write({"pin_code": ""})  # XXX
        m = get_model(obj.approve_model)
        f = getattr(m, obj.approve_method, None)
        if not f:
            raise Exception("Invalid method %s of %s" % (obj.approve_method, obj.approve_model))
        if not obj.approver_id:
            res = f([obj.approve_id], context=context)
        else:
            db = database.get_connection()
            res = db.get("SELECT pin_code FROM base_user WHERE id=%s", obj.approver_id.id)
            enc_pin_code = res.pin_code
            if not utils.check_password(pin_code, enc_pin_code):
                raise Exception("Wrong PIN")
            user_id = get_active_user()
            set_active_user(obj.approver_id.id)
            try:
                res = f([obj.approve_id], context=context)
            finally:
                set_active_user(user_id)
        return res

ApproveWizard.register()
