<div>
    <div style={{marginBottom:10}}>
        <strong>Make a payment</strong>
    </div>
    <div class="row">
        {{view "field" name="amount" span="2" form_layout="stacked" context=context}}
        {{view "field" name="date" span="2" form_layout="stacked" context=context}}
        {{view "field" name="account_id" span="2" form_layout="stacked" condition='[["type","!=","view"],["company_id","=",context.company_id]]' context=context}}
        {{view "field" name="ref" span="2" form_layout="stacked" context=context}}
        {{view "field" name="invoice_id" invisible="1" context=context}}
        <div class="span2" style="padding-top:10px">
            {{view "button" string="Add Payment" method="add_payment" type="success" icon="ok" icon_white="1" context=context}}
        </div>
    </div>
</div>
