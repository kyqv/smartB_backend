from netforce.model import Model,fields,get_model

class DeliverySlotCapacity(Model):
    _name="delivery.slot.capacity"
    _string="Delivery Slot Capacity"
    _fields={
        "slot_id": fields.Many2One("delivery.slot","Delivery Slot",required=True,on_delete="cascade"),
        "weekday": fields.Selection([["0","Monday"],["1","Tuesday"],["2","Wednesday"],["3","Thursday"],["4","Friday"],["5","Saturday"],["6","Sunday"]],"Weekday"),
        "capacity": fields.Integer("Capacity",required=True),
        "exclude_postal_codes": fields.Text("Exclude Postal Codes"),
    }

DeliverySlotCapacity.register()
