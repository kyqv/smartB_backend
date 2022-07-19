import time

from netforce.model import Model, fields

FMT_TIME='%Y-%m-%d %H:%M:%S'
FMT_DAY='%Y-%m-%d'

class Holiday(Model):
    _name="hr.holiday"
    _string="Holiday"
    _fields={
        "name": fields.Char("Name",search=True),
        "date": fields.Date("Date",required=True,search=True),
        "description": fields.Text("Description"),
        "comments": fields.One2Many("message","related_id","Comments"),
        'generic': fields.Boolean("Generic"),
    }
    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "comday": False,
        'generic': False,
    }
    _order="date"

    __sql_constraints=[
        ("hr_holiday_date_uniq","unique (date)","Date should be unique"),
    ]

    def get_holidays(self,context={}):
        date_from=context.get('start_date', time.strftime(FMT_DAY))
        date_to=context.get('end_date', time.strftime(FMT_DAY))
        dom=[
            ['date','>=',date_from],
            ['date','<=',date_to],
        ]
        res=set()
        for r in self.search_read(dom,['date']):
            res.update({r['date']})
        yearnow,month,date=time.strftime(FMT_DAY).split("-")
        dom=[['generic','=',True]]
        for r in self.search_read(dom,['date']):
            y,m,d=r['date'].split("-")
            date='-'.join([yearnow,m,d])
            res.update({date})
        return list(res)

Holiday.register()


