<div>
    <div style={{float:"right",width:140}}>
        <a href="/action?name=cust_invoice&tab_no=4" style={{fontSize:12}}>Overdue Invoices ({data.overdue_count})</a>
        <br/>
        <b>{currency(data.overdue_amount)}</b>
    </div>
    <div style={{float:"right",width:140}}>
        <a href="/action?name=cust_invoice&tab_no=2" style={{fontSize:12}}>Draft Invoices ({data.draft_count})</a>
        <br/>
        <b>{currency(data.draft_amount)}</b>
    </div>
    <Button string="New Receivable Invoice" size="sm" icon="plus" action="cust_invoice" action_options='{"mode":"form","form_layout":"cust_invoice_form","context":{"defaults":{"type":"out","inv_type":"invoice"}}}'/>
    <Chart chart_type="bar" height={150} data={data.chart_data}/>
</div>
