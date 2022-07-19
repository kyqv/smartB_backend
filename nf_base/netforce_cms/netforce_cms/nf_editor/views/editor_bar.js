var EditorBar=Backbone.View.extend({
    template: Handlebars.templates.editor_bar,

    events: {
        "click .edit": "click_edit",
        "click .cancel": "click_cancel",
        "click .save": "click_save",
    },

    render: function() {
        var data={
            mode_edit: this.mode=="edit",
        };
        var html=this.template(data);
        this.$el.html(html);
        this.$el.css({"background-color":"#333","line-height":"30px","padding-left":"14px"});
    },

    click_edit: function(e) {
        console.log("click_edit");
        e.preventDefault();
        this.create_editors();
        this.mode="edit";
        this.render();
    },

    click_cancel: function(e) {
        console.log("click_cancel");
        e.preventDefault();
        this.restore_original_data();
        this.destroy_editors();
        this.mode="view";
        this.render();
    },

    click_save: function(e) {
        console.log("click_save");
        e.preventDefault();
        res=confirm("Save data?");
        if (!res) return;
        this.save_data();
        this.destroy_editors();
        this.mode="view";
        this.render();
    },

    create_editors: function() {
        $(".nf-editable").each(function() {
            console.log("create editor",this);
            var el=this;
            var text_only=$(el).data("text-only");
            $(el).attr("contenteditable","true");
            if (text_only) {
                $(el).data("original_data",$(el).text());
            } else {
                var editor=CKEDITOR.inline(el,{
                    allowedContent: true,
                    extraPlugins: "richcombo,colorbutton,font,justify,undo,nf_toolbar,nf_alert,nf_badge,nf_button,nf_carousel,nf_columns,nf_image,nf_jumbotron,nf_label,nf_well",
                    toolbar: [
                        ["NFAddWidget"],
                        ["Bold","Italic","Underline","Strike"],
                        ["FontSize"],
                        ["TextColor","BGColor"],
                        ["Link"],
                        ['JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'],
                        ["BulletedList","NumberedList"],
                        ["RemoveFormat"],
                        ["Undo","Redo"],
                    ]
                });
                $(el).data("editor",editor);
                setTimeout(function() { // XXX: if don't put timeout, original_data always different than data...
                    $(el).data("original_data",editor.getData());
                },500);
            }
        });
    },

    destroy_editors: function() {
        $(".nf-editable").each(function() {
            var el=this;
            $(el).removeAttr("contenteditable");
            var editor=$(el).data("editor");
            if (editor) {
                editor.destroy();
            }
        });
    },

    restore_original_data: function() {
        console.log("restore_original_data");
        $(".nf-editable").each(function() {
            var el=this;
            var data=$(el).data("original_data");
            $(el).html(data);
        });
    },

    save_data: function() {
        console.log("save_data");
        $(".nf-editable").each(function() {
            var el=this;
            var editor=$(el).data("editor");
            var model=$(el).data("model");
            var field=$(el).data("field");
            if (!model || !field) return;
            var id=$(el).data("id");
            if (editor) {
                var data=editor.getData();
            } else {
                var data=$(el).text();
            }
            var original_data=$(el).data("original_data");
            if (data==original_data) return;
            console.log("data0",original_data);
            console.log("data1",data);
            var vals={};
            vals[field]=data;
            console.log("saving data",model,field,id);
            if (id) {
                rpc_execute(model,"write",[[id],vals],{},function(err) {
                    if (err) {
                        console.log("Failed to save data (write)",err);
                        return;
                    }
                });
            } else {
                var defaults=$(el).data("defaults");
                _.extend(vals,defaults);
                rpc_execute(model,"create",[vals],{},function(err) {
                    if (err) {
                        console.log("Failed to save data (create)",err);
                        return;
                    }
                });
            }
        });
    },
});
