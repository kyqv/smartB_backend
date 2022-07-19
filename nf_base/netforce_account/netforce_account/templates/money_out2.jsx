<div>
    <div style={{float:"right",width:120}}>
        <a href="/action?name=supp_invoice&tab_no=4" style={{fontSize:12}}>Overdue Invoices ({data.overdue_count})</a>
        <br/>
        <b>{data.overdue_amount}</b>
    </div>
    <div style={{float:"right",width:120}}>
        <a href="/action?name=supp_invoice&tab_no=2" style={{fontSize:12}}>Draft Invoices ({data.draft_count})</a>
        <br/>
        <b>{data.draft_amount}</b>
    </div>
    <Button string="New Payable Invoice" size="sm" icon="plus" action="supp_invoice" action_options='{"mode":"form","form_layout":"supp_invoice_form","context":{"defaults":{"type":"in","inv_type":"invoice"}}}'/>
    <Chart chart_type="bar" x_type="datetime" height={150} data={data.chart_data}/>
</div>
