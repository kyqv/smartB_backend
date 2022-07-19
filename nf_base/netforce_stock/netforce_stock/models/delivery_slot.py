from netforce.model import Model,fields,get_model

class DeliverySlot(Model):
    _name="delivery.slot"
    _string="Delivery Slots"
    _key=["name"]
    _fields={
        "sequence": fields.Integer("Sequence"),
        "name": fields.Char("Name",required=True),
        "time_from": fields.Char("From Time",required=True),
        "time_to": fields.Char("To Time",required=True),
        "capacities": fields.One2Many("delivery.slot.capacity","slot_id","Capacities"),
    }

DeliverySlot.register()
