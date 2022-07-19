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

# just to trigger sales order 'delivered' event...
class Picking(Model):
    _inherit="stock.picking"

    def set_done(self,ids,context={}): 
        sale_ids=[]
        for obj in self.browse(ids):
            for line in obj.lines:
                rel=line.related_id
                if not rel:
                    continue
                if rel._model!="sale.order":
                    continue
                sale_ids.append(rel.id)
        sale_ids=list(set(sale_ids))
        sale_ids=[int(i) for i in sale_ids]
        undeliv_sale_ids=[]
        for sale in get_model("sale.order").browse(sale_ids):
            if not sale.is_delivered:
                undeliv_sale_ids.append(sale.id)
        res=super().set_done(ids,context=context)
        deliv_sale_ids=[]
        for sale in get_model("sale.order").browse(undeliv_sale_ids):
            if sale.is_delivered:
                deliv_sale_ids.append(sale.id)
        if deliv_sale_ids:
            get_model("sale.order").trigger(deliv_sale_ids,"delivered")
        return res

Picking.register()
