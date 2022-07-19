from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="general.address"
    _version="1.116.0"

    def migrate(self):
        for obj in get_model("address").search_browse([["address","=",None]]):
            vals={}
            comps=[]
            if obj.unit_no:
                comps.append(obj.unit_no)
            if obj.floor:
                comps.append("Floor: %s"%obj.floor)
            if obj.bldg_name:
                comps.append(obj.bldg_name)
            if obj.bldg_no:
                comps.append(obj.bldg_no)
            if obj.village:
                comps.append(obj.village)
            if obj.soi:
                comps.append(obj.soi)
            if obj.street:
                comps.append(obj.street)
            vals["address"]=", ".join(comps)
            comps=[]
            if obj.sub_district:
                comps.append(obj.sub_district)
            if obj.district:
                comps.append(obj.district)
            vals["address2"]=",".join(comps)
            obj.write(vals)

Migration.register()
