CKEDITOR.plugins.add('nf_badge', {
    requires: 'widget',
    icons: 'nf_badge',

    init: function( editor ) {
        editor.widgets.add( 'nf_badge', {
            editables: {
                content: {
                    selector: '.nf-badge-content',
                }
            },

            template:
                '<span class="nf-badge badge badge-default">'+
                '<span class="nf-badge-content">Content...</span>'+
                '</span>',

            upcast: function( element ) {
                return element.name == 'div' && element.hasClass( 'nf-badge' );
            }
        } );
    }
});
