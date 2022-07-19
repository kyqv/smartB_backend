<div className="nf-table-container">
    <table className="table table-bordered table-striped table-condensed">
        <thead>
            <tr>
                <th>
                    Resource
                </th>
                <th>
                    This Week
                </th>
                <th>
                    Last Week
                </th>
                <th>
                    Week-2
                </th>
                <th>
                    Week-3
                </th>
                <th>
                    Week-4
                </th>
                <th>
                    Week-5
                </th>
                <th>
                    Week-6
                </th>
                <th>
                    Week-7
                </th>
                <th>
                    Older
                </th>
            </tr>
        </thead>
        <tbody>
            {data.lines.map((l)=>{
                <tr>
                    <td>
                        {l.resource_name}
                    </td>
                    {l.weeks.map((w)=>{
                        <td>
                            {w.bill_hours} / {w.actual_hours}
                        </td>
                    })}
                    <td>
                        {l.older.bill_hours} / {l.older.actual_hours}
                    </td>
                </tr>
            })}
        </tbody>
    </table>
</div>
