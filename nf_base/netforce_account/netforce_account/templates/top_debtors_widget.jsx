<div>
    <div className="nf-board-widget-title"><h3>Top 10 Debtors</h3></div>
    <table className="table">
        <thead>
            <tr>
                <th>{t("Contact")}</th>
                <th style={{textAlign:"right"}}>{t("Outstanding")}</th>
                <th style={{textAlign:"right"}}>{t("Overdue")}</th>
            </tr>
        </thead>
        <tbody>
            {data.map((l)=>{
                return <tr>
                    <td>{l.contact_name}</td>
                    <td style={{textAlign:"right"}}>{currency(l.amount_due)}</td>
                    <td style={{textAlign:"right"}}>{currency(l.amount_overdue)}</td>
                </tr>
            })}
        </tbody>
    </table>
</div>
