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

from netforce.controller import Controller
from netforce import config
from netforce.model import get_model
from netforce.database import get_connection

class Trigger(Controller):
    _path="/trigger"

    def get(self):
        try:
            model=self.get_argument("model")
            ids=self.get_argument("ids",None)
            event=self.get_argument("event",None)
            if not event:
                raise Exception("Missing event")
            m=get_model(model)
            if ids:
                ids=[int(x) for x in ids.split(",")]
            m.trigger(ids,event)
            self.write("OK")
            db=get_connection()
            db.commit()
        except Exception as e:
            import traceback
            traceback.print_exc()
            db=get_connection()
            db.rollback()
            self.write("ERROR: %s"%e)

Trigger.register()
