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
import time
from netforce.database import get_connection
from netforce_report import render_template_hbs


class Message(Model):
    _name = "message"
    _string = "Message"
    _fields = {
        "date": fields.DateTime("Date", required=True, search=True),
        "from_id": fields.Many2One("base.user", "From User", required=True, search=True),
        "to_id": fields.Many2One("base.user", "To User", search=True),
        "subject": fields.Char("Subject", search=True),
        "body": fields.Text("Message Body", required=True, search=True),
        "attach": fields.File("Attachment"),
        "ref_uuid": fields.Char("Reference UUID"),
        "related_id": fields.Reference([], "Related To"),
        "state": fields.Selection([["new", "New"], ["opened", "Opened"]], "Status", required=True, search=True),
        "open_dummy": fields.Boolean("Open Dummy", function="get_open_dummy"),
    }
    _order = "date desc"
    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "from_id": lambda *a: get_active_user(),
        "state": "new",
    }

    def create(self, vals, **kw):
        new_id = super().create(vals, **kw)
        to_id = vals.get("to_id")
        if to_id:
            db = get_connection()
            get_model("ws.event").new_event("new_message", to_id)
        self.trigger([new_id], "created")
        return new_id

    def get_open_dummy(self, ids, context={}):
        vals = {}
        user_id = get_active_user()
        for obj in self.browse(ids):
            if user_id == obj.to_id.id:
                obj.write({"state": "opened"})
            vals[obj.id] = True
        return vals

    def send_from_template(self, template=None, from_user=None, to_user=None, context={}):
        print("####################################################")
        print("Message.send_from_template", template, from_user, to_user)
        res = get_model("message.tmpl").search([["name", "=", template]])
        if not res:
            raise Exception("Template not found: %s" % template)
        tmpl_id = res[0]
        tmpl = get_model("message.tmpl").browse(tmpl_id)
        try:
            trigger_model = context.get("trigger_model")
            if not trigger_model:
                raise Exception("Missing trigger model")
            print("trigger_model", trigger_model)
            tm = get_model(trigger_model)
            trigger_ids = context.get("trigger_ids")
            if trigger_ids is None:
                raise Exception("Missing trigger ids")
            print("trigger_ids", trigger_ids)
            user_id = get_active_user()
            user = get_model("base.user").browse(user_id)
            for obj in tm.browse(trigger_ids):
                tmpl_ctx = {"obj": obj, "user": user}
                from_user_ = from_user
                if not from_user_:
                    try:
                        from_user_ = render_template_hbs(tmpl.from_user or "", tmpl_ctx)
                    except:
                        raise Exception("Error in 'From User': %s" % tmpl.from_user)
                if not from_user_:
                    raise Exception("Missing 'From User'")
                res = get_model("base.user").search([["login", "=", from_user_]])
                if not res:
                    raise Exception("'From User' not found: %s" % from_user_)
                from_id = res[0]
                to_user_ = to_user
                if not to_user_:
                    try:
                        to_user_ = render_template_hbs(tmpl.to_user or "", tmpl_ctx)
                    except:
                        raise Exception("Error in 'To User': %s" % tmpl.to_user)
                if not to_user_:
                    raise Exception("Missing 'To User'")
                to_ids = []
                for login in [x.strip() for x in to_user_.split(",")]:
                    res = get_model("base.user").search([["login", "=", login]])
                    if not res:
                        raise Exception("'To User' not found: %s" % login)
                    to_id = res[0]
                    to_ids.append(to_id)
                try:
                    subject = render_template_hbs(tmpl.subject, tmpl_ctx)
                except:
                    raise Exception("Error in  'Subject': %s" % tmpl.subject)
                try:
                    body = render_template_hbs(tmpl.body, tmpl_ctx)
                except:
                    raise Exception("Error in 'Body': %s" % tmpl.body)
                for to_id in to_ids:
                    vals = {
                        "from_id": from_id,
                        "to_id": to_id,
                        "subject": subject,
                        "body": body,
                    }
                    self.create(vals)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise Exception("Error in template %s: %s" % (template, e))

Message.register()
