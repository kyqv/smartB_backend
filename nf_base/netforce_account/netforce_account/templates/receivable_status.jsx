<div>
    <div className="nf-board-widget-title">
        <h3>{t("Items By Status")}</h3>
    </div>
    <table className="table">
        <thead>
            <tr>
                <th>{t("Status")}</th>
                <th style={{textAlign: "right"}}>{t("Total")}</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>
                    Draft ({data.draft.count})
                </td>
                <td style={{textAlign: "right"}}>
                    {currency(data.draft.amount)}
                </td>
            </tr>
            <tr>
                <td>
                    Awaiting Approval ({data.waiting_approval.count})
                </td>
                <td style={{textAlign: "right"}}>
                    {currency(data.waiting_approval.amount)}
                </td>
            </tr>
            <tr>
                <td>
                    Awaiting Payment ({data.waiting_payment.count})
                </td>
                <td style={{textAlign: "right"}}>
                    {currency(data.waiting_payment.amount)}
                </td>
            </tr>
        </tbody>
    </table>
</div>
