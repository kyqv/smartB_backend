<div>
    <center>
        <h2>
            Stock Summary
        </h2>
        <h3>
            {data.company_name}
        </h3>
        <h4>
            From {data.date_from} to {data.date_to}
            <If condition={data.product_id}>
                <br/>
                Product: {data.product_id[1]}
            </If>
            <If condition={data.lot_num}>
                <br/>
                Lot / Serial Number: {data.lot_num}
            </If>
            <If condition={data.location_id}>
                <br/>
                Location: {data.location_id[1]}
            </If>
            <If condition={data.container_id}>
                <br/>
                Container: {data.container_id[1]}
            </If>
        </h4>
    </center>
    <table className="table table-bordered">
        <thead>
            <tr>
                <th></th>
                <th></th>
                <If condition={data.show_lot}>
                    <th></th>
                </If>
                <th></th>
                <If condition={data.show_container}>
                    <th></th>
                </If>
                <th></th>
                <If condition={!data.only_closing}>
                    <th colSpan={data.show_qty2?3:2} style={{textAlign: "center"}}>
                        Opening
                    </th>
                    <th colSpan={data.show_qty2?3:2} style={{textAlign: "center"}}>
                        Incoming
                    </th>
                    <th colSpan={data.show_qty2?3:2} style={{textAlign: "center"}}>
                        Outgoing
                    </th>
                </If>
                <th colSpan={data.show_qty2?3:2} style={{textAlign: "center"}}>
                    Closing
                </th>
            </tr>
            <tr>
                <th>
                    Product Code
                </th>
                <th>
                    Product Name
                </th>
                <If condition={data.show_lot}>
                    <th>
                        Lot / Serial Number
                    </th>
                </If>
                <th>
                    Location
                </th>
                <If condition={data.show_container}>
                    <th>
                        Container
                    </th>
                </If>
                <th>
                    UoM
                </th>
                <If condition={!data.only_closing}>
                    <th>
                        Qty 
                    </th>
                    <th>
                        Amount
                    </th>
                    <If condition={data.show_qty2}>
                        <th>
                            Secondary Qty
                        </th>
                    </If>
                    <th>
                        Qty 
                    </th>
                    <th>
                        Amount
                    </th>
                    <If condition={data.show_qty2}>
                        <th>
                            Secondary Qty
                        </th>
                    </If>
                    <th>
                        Qty 
                    </th>
                    <th>
                        Amount
                    </th>
                    <If condition={data.show_qty2}>
                        <th>
                            Secondary Qty
                        </th>
                    </If>
                </If>
                <th>
                    Qty 
                </th>
                <th>
                    Amount
                </th>
                <If condition={data.show_qty2}>
                    <th>
                        Secondary Qty
                    </th>
                </If>
            </tr>
        </thead>
        <tbody>
            {data.lines.map((l,i)=>{
                return <tr key={i}>
                    <td>
                        {l.prod_code}
                    </td>
                    <td>
                        {l.prod_name}
                    </td>
                    <If condition={data.show_lot}>
                        <td>
                            <Link to={"/action?name=stock_lot&mode=form&active_id="+l.lot_id}/>
                        </td>
                    </If>
                    <td>
                        {l.loc_name}
                    </td>
                    <If condition={data.show_container}>
                        <td>
                            {l.cont_name}
                        </td>
                    </If>
                    <td>
                        {l.uom_name}
                    </td>
                    <If condition={!data.only_closing}>
                        <td>
                            {fmt_qty(l.open_qty)}
                        </td>
                        <td>
                            {fmt_money(l.open_amt)}
                        </td>
                        <If condition={data.show_qty2}>
                            <td>
                                {fmt_qty(l.open_qty2)}
                            </td>
                        </If>
                        <td>
                            {fmt_qty(l.period_in_qty)}
                        </td>
                        <td>
                            {fmt_money(l.period_in_amt)}
                        </td>
                        <If condition={data.show_qty2}>
                            <td>
                                {fmt_qty(l.period_in_qty2)}
                            </td>
                        </If>
                        <td>
                            {fmt_qty(l.period_out_qty)}
                        </td>
                        <td>
                            {fmt_money(l.period_out_amt)}
                        </td>
                        <If condition={data.show_qty2}>
                            <td>
                                {fmt_qty(l.period_out_qty2)}
                            </td>
                        </If>
                    </If>
                    <td>
                        <Link to={"/action#name=report_stock_card&defaults.product_id="+l.prod_id+"&defaults.location_id="+l.loc_id+"&defaults.date_from="+data.date_from+"&defaults.date_to="+data.date_to+"&defaults.lot_id="+l.lot_id}>
                            {fmt_qty(l.close_qty)}
                        </Link>
                    </td>
                    <td>
                        <Link to={"/action#name=report_stock_card&defaults.product_id="+l.prod_id+"&defaults.location_id="+l.loc_id+"&defaults.date_from="+data.date_from+"&defaults.date_to="+data.date_to+"&defaults.lot_id="+l.lot_id}>
                            {fmt_money(l.close_amt)}
                        </Link>
                    </td>
                    <If condition={data.show_qty2}>
                        <td>
                            {fm_qty(l.close_qty2)}
                        </td>
                    </If>
                </tr>
            })}
        </tbody>
        <tfoot>
            <tr>
                <td></td>
                <td></td>
                <If condition={data.show_lot}>
                    <td></td>
                </If>
                <td></td>
                <If condition={data.show_container}>
                    <td></td>
                </If>
                <td></td>
                <If condition={!data.only_closing}>
                    <td></td>
                    <th>
                        {fmt_money(data.total_open_amt)}
                    </th>
                    <If condition={data.show_qty2}>
                        <th>
                            {fmt_qty(data.total_open_qty2)}
                        </th>
                    </If>
                    <td></td>
                    <th>
                        {fmt_money(data.total_period_in_amt)}
                    </th>
                    <If condition={data.show_qty2}>
                        <th>
                            {fmt_qty(data.total_period_in_qty2)}
                        </th>
                    </If>
                    <td></td>
                    <th>
                        {fmt_money(data.total_period_out_amt)}
                    </th>
                    <If condition={data.show_qty2}>
                        <th>
                            {fmt_qty(data.total_period_out_qty2)}
                        </th>
                    </If>
                </If>
                <th>
                    {fmt_qty(data.total_close_qty)}
                </th>
                <th>
                    {fmt_money(data.total_close_amt)}
                </th>
                <If condition={data.show_qty2}>
                    <th>
                        {fmt_qty(data.total_close_qty2)}
                    </th>
                </If>
            </tr>
        </tfoot>
    </table>
</div>
