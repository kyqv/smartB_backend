CKEDITOR.plugins.add('nf_well', {
    requires: 'widget',
    icons: 'nf_well',

    init: function( editor ) {
        editor.widgets.add( 'nf_well', {
            editables: {
                content: {
                    selector: '.nf-well-content',
                }
            },

            template:
                '<div class="nf-well">'+
                '<div class="well nf-well-content">'+
                '<p>Content...</p>'+
                '</div>'+
                '</div>',

            upcast: function( element ) {
                return element.name == 'div' && element.hasClass( 'nf-well' );
            }
        } );
    }
});
