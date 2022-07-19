from netforce.model import Model, fields, get_model
from netforce.access import get_active_company

class PayRunJournal(Model):
    _name="hr.payrun.journal"
    _transient=True
    
    def _get_all(self,ids,context={}):
        res={}
        for obj in self.browse(ids):
            total_credit=0
            total_debit=0
            for line in obj.lines:
                total_credit+=line.credit  or 0 
                total_debit+=line.debit  or 0 
            res[obj.id]={
                'total_credit': total_credit,
                'total_debit': total_debit,
            }
        return res

    _fields={
        'name': fields.Char("Name"),
        "payrun_id": fields.Many2One("hr.payrun","Payrun",required=True,on_delete="cascade"),
        'note': fields.Text("Note"),
        'lines': fields.One2Many("hr.payrun.journal.line","payrun_journal_id","Lines"),
        'total_credit': fields.Decimal("Credit",function="_get_all",function_multi=True),
        'total_debit': fields.Decimal("Debit",function="_get_all",function_multi=True),
    }

    def _get_payrun(self,context={}):
        payrun_id=context.get("refer_id")
        if not payrun_id:
            return None
        payrun_id=int(payrun_id)
        return payrun_id

    def _get_lines(self,context={}):
        payrun_id=context.get("refer_id")
        if not payrun_id:
            return None
        payrun_id=int(payrun_id)
        lines=[]
        if payrun_id:
            payrun=get_model("hr.payrun").browse(payrun_id)
            payslip_ids=[payslip.id for payslip in payrun.payslips]
            lines=get_model('hr.payslip').get_move_lines(payslip_ids)
        return lines
    
    def _get_total_credit(self,context={}):
        payrun_id=context.get("refer_id")
        if not payrun_id:
            return None
        payrun_id=int(payrun_id)
        lines=[]
        if payrun_id:
            payrun=get_model("hr.payrun").browse(payrun_id)
            payslip_ids=[payslip.id for payslip in payrun.payslips]
            lines=get_model('hr.payslip').get_move_lines(payslip_ids)
        total_credit=0
        for line in lines:
            total_credit+=line['credit'] or 0
        return total_credit

    def _get_total_debit(self,context={}):
        payrun_id=context.get("refer_id")
        if not payrun_id:
            return None
        payrun_id=int(payrun_id)
        lines=[]
        if payrun_id:
            payrun=get_model("hr.payrun").browse(payrun_id)
            payslip_ids=[payslip.id for payslip in payrun.payslips]
            lines=get_model('hr.payslip').get_move_lines(payslip_ids)
        total_debit=0
        for line in lines:
            total_debit+=line['debit'] or 0
        return total_debit

    _defaults={
            'payrun_id': _get_payrun,
            'name': _get_payrun,
            'lines': _get_lines,
            'total_credit': _get_total_credit,
            'total_debit': _get_total_debit,
    }

    def post(self,ids,context={}):
        obj=self.browse(ids)[0]
        if obj.total_debit != obj.total_credit:
            raise Exception("Debit & Credit is not balance!")
        payrun=obj.payrun_id
        company_id=get_active_company()
        move=payrun.move_id
        if move:
            move.to_draft()
            for line in move.lines:
                line.delete()
        pst=get_model("hr.payroll.settings").browse(1)
        journal=pst.journal_id
        if not journal:
            raise Exception("Please define journal in payroll setting.")
        if not move:
            move_vals={
                "journal_id": journal.id,
                "number": payrun.number,
                "date": payrun.date_pay,
                "narration": 'Paid Payroll %s'%(payrun.date_pay),
                "related_id": "hr.payrun,%s"%payrun.id,
                "company_id": company_id,
            }
            move_id=get_model("account.move").create(move_vals)
            move=get_model("account.move").browse(move_id)
        lines=[]
        for line in obj.lines:
            lines.append(('create',{
                'description': line.description or "",
                'debit': line.debit or 0,
                'credit': line.credit or 0,
                'account_id': line.account_id.id,
            }))
        move.write({
            'lines': lines,
        })
        move.post()
        for payslip in payrun.payslips:
            payslip.write({
                'move_id': move.id,
                'state': 'posted',
            })
        payrun.write({
            'move_id': move.id,
            'state': 'posted',
        })
        return {
            'next': {
                'name': 'payrun',
                'mode': 'form',
                'active_id': payrun.id,
            },
            'flash': 'payrun %s has been posted!'%payrun.number,
        }
    
    def update_amount(self,data={}):
        data['total_credit']=0
        data['total_debit']=0
        for line in data['lines']:
            data['total_debit']+=line['debit'] or 0
            data['total_credit']+=line['credit'] or 0
        return data

    def onchange_line(self,context={}):
        data=context['data']
        #path=context['path']
        #line=get_data_path(data,path,parent=True)
        data=self.update_amount(data)
        return data

PayRunJournal.register()
