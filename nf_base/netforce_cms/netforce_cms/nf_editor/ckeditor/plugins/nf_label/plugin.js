CKEDITOR.plugins.add('nf_label', {
    requires: 'widget',
    icons: 'nf_label',

    init: function( editor ) {
        editor.widgets.add( 'nf_label', {
            editables: {
                content: {
                    selector: '.nf-label-content',
                }
            },

            template:
                '<span class="nf-label label label-default">'+
                '<span class="nf-label-content">Content...</span>'+
                '</span>',

            upcast: function( element ) {
                return element.name == 'div' && element.hasClass( 'nf-label' );
            }
        } );
    }
});
