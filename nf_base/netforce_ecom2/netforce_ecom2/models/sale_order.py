from netforce.model import Model,fields,get_model
from netforce import access

class SaleOrder(Model):
    _inherit="sale.order"
    _fields={
        "ecom_state": fields.Selection([
            ["wait_packing","Waiting Packing"],
            ["wait_payment","Waiting Payment"],
            ["wait_ship","Waiting Shipment"],
            ["wait_delivery","Waiting Delivery"],
            ["done","Finished"],
            ["canceled","Canceled"],
            ["ship_error","Can not deliver"]
            ],"Ecommerce Frontend Status",function="get_ecom_state",search=True),
    }

    def get_ecom_state(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            if obj.state=="voided":
                state="canceled"
            elif not obj.invoices:
                state="wait_packing"
            else:
                inv=obj.invoices[0]
                if inv.amount_due>0: 
                    state="wait_payment"
                else:
                    ship_states={}
                    for pick in obj.pickings:
                        ship_states.setdefault(pick.ship_state,[]).append(pick.id)
                    if None in ship_states or "wait_pick" in ship_states:
                        state="wait_ship"
                    elif "in_transit" in ship_states:
                        state="wait_delivery"
                    elif "error" in ship_states:
                        state="ship_error"
                    else:
                        state="done"
            vals[obj.id]=state
        return vals

    def save_pay_method(self,ids,pay_method_id,context={}): # XXX: remove later
        access.set_active_company(1) # XXX
        obj=self.browse(ids[0])
        obj.write({"pay_method_id":pay_method_id})

SaleOrder.register()
