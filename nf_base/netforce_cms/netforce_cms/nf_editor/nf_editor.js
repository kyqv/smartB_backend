function rpc_execute(model,method,args,opts,cb) {
    console.log("RPC",model,method,args,opts);
    var params=[model,method];
    params.push(args);
    if (opts) {
        params.push(opts);
    }
    $.ajax({
        url: "/json_rpc",
        type: "POST",
        data: JSON.stringify({
            id: (new Date()).getTime(),
            method: "execute",
            params: params
        }),
        dataType: "json",
        contentType: "application/x-www-form-urlencoded; charset=UTF-8",
        success: function(data) {
            if (data.error) {
                console.log("RPC ERROR",model,method,data.error.message);
            } else {
                console.log("RPC OK",model,method,data.result);
            }
            if (cb) {
                cb(data.error,data.result);
            }
        },
        error: function() {
            console.log("RPC ERROR",model,method);
        }
    });
}

$(function() {
    var editor_bar=new EditorBar();
    editor_bar.render();
    $("body").prepend(editor_bar.el);
});
