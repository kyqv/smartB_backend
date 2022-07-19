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
import json
from netforce import access

class Message(Model):
    _inherit = "message"

    def create(self,vals,*args,**kw):
        new_id=super().create(vals,*args,**kw)
        obj=self.browse(new_id)
        user_id=access.get_active_user()
        user=get_model("base.user").browse(user_id)
        if obj.related_id._model=="issue":
            issue=obj.related_id
            project=issue.project_id
            contact=issue.contact_id
            emails=issue.get_email_addresses()
            subject="New message by %s for issue %s"%(user.name,issue.number)
            if obj.subject:
                subject+=": %s"%obj.subject
            if emails:
                vals={
                    "from_addr": "support@netforce.com", # XXX
                    "to_addrs": ",".join(emails),
                    "subject": subject,
                    "body": obj.body,
                    "state": "to_send",
                    "name_id": "contact,%s"%contact.id,
                    "related_id": "issue,%s"%issue.id,
                }
                get_model("email.message").create(vals)
        return new_id

Message.register()
