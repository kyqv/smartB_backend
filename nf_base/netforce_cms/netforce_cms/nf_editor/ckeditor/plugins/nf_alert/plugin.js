CKEDITOR.plugins.add('nf_alert', {
    requires: 'widget',
    icons: 'nf_alert',

    init: function( editor ) {
        editor.widgets.add( 'nf_alert', {
            editables: {
                content: {
                    selector: '.nf-alert-content',
                }
            },

            template:
                '<div class="nf-alert">'+
                '<div class="alert alert-success nf-alert-content">'+
                '<p>Content...</p>'+
                '</div>'+
                '</div>',

            upcast: function( element ) {
                return element.name == 'div' && element.hasClass( 'nf-alert' );
            }
        } );
    }
});
