CKEDITOR.plugins.add('nf_toolbar', {
    requires: 'widget',
    icons: 'nf_toolbar',

    init: function( editor ) {
        editor.ui.addRichCombo('NFAddWidget',{
            label: "Add Widget",
            title: "Add Widget",
            multiSelect: false,
            init: function () {
                this.add("nf_alert","Alert","Alert");
                this.add("nf_badge","Badge","Badge");
                this.add("nf_button","Button","Button");
                this.add("nf_carousel","Carousel","Carousel");
                this.add("nf_columns","Columns","Columns");
                this.add("nf_image","Image","Image");
                this.add("nf_jumbotron","Jumbotron","Jumbotron");
                this.add("nf_label","Label","Label");
                this.add("nf_well","Well","Well");
            },
            onClick: function (value) {
                editor.execCommand(value);
            },
        });
    }
});
