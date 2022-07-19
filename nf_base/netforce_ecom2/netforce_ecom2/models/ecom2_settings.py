from netforce.model import Model,fields,get_model

class Settings(Model):
    _name="ecom2.settings"
    _string="Settings"
    _fields={
        "delivery_slot_discount": fields.Decimal("Same Delivery Slot Discount"),
        "delivery_max_days": fields.Integer("Delivery Max Days"),
        "delivery_min_hours": fields.Integer("Delivery Min Hours"),
        "ecom_num_lots": fields.Integer("Number Of Lots To Show On Website"),
        "sale_lead_time_nostock": fields.Integer("Sale Lead Time When Out Of Stock (Days)"),
        "ecom_return_url": fields.Char("Return URL of ecommerce frontend"),
        "extra_ship_addresses": fields.One2Many("address","related_id","Extra Shipping Addresses"),
        "work_time_start": fields.Char("Work Time Start"),
        "work_time_end": fields.Char("Work Time End"),
    }

Settings.register()
