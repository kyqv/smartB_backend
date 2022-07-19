from netforce.model import Model, fields

class LeavePeriod(Model):
    _name="hr.leave.period"
    _string="Leave Period"
    _name_field="date_from" # XXX
    _fields={
        "leave_type_id": fields.Many2One("hr.leave.type", "Leave Type", required=True, search=True),
        "date_from": fields.Date("From Date", required=True, search=True),
        "date_to": fields.Date("To Date", required=True, search=True),
        "max_date": fields.Date("Max Date", search=True),
        "max_days": fields.Decimal("Max Days", search=True),
    }
    _order="date_from"

    def name_search(self,name,condition=[],limit=None,context={}):
        ids=self.search(condition,limit=limit)
        return self.name_get(ids,context)

    def name_get(self,ids,context={}):
        vals=[]
        for obj in self.browse(ids):
            leave_name=obj.leave_type_id.name or ''
            name=leave_name+" "+"%s - %s"%(obj.date_from,obj.date_to)
            vals.append((obj.id,name))
        return vals

    def import_get(self,name,context={}):
        parent_vals=context["parent_vals"]
        leave_type_id=parent_vals["leave_type_id"]
        res=name.split(" - ")
        if len(res)!=2:
            raise Exception("Invalid leave period format: '%s'"%name)
        date_from,date_to=res
        cond=[["leave_type_id","=",leave_type_id],["date_from","=",date_from],["date_to","=",date_to]]
        res=self.search(cond)
        if not res:
            raise Exception("Leave period not found")
        return res[0]

LeavePeriod.register()
