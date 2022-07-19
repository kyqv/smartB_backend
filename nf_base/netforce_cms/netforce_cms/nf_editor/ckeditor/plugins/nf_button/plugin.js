CKEDITOR.plugins.add('nf_button', {
    requires: 'widget',
    icons: 'nf_button',

    init: function( editor ) {
        editor.widgets.add( 'nf_button', {
            editables: {
                content: {
                    selector: '.nf-button-content',
                }
            },

            template:
                '<button type="button" class="btn btn-default nf-button">'+
                '<span class="nf-button-content">Content...</span>'+
                '</button>',

            upcast: function( element ) {
                return element.name == 'div' && element.hasClass( 'nf-button' );
            }
        } );
    }
});
