CKEDITOR.plugins.add('nf_columns', {
    requires: 'widget',
    icons: 'nf_columns',

    init: function( editor ) {
        editor.widgets.add( 'nf_columns', {
            editables: {
                content1: {
                    selector: '.nf-columns-content1',
                },
                content2: {
                    selector: '.nf-columns-content2',
                },
            },

            template:
                '<div class="row nf-columns">'+
                '<div class="col-md-6 nf-columns-content1"><p>Content...</p></div>'+
                '<div class="col-md-6 nf-columns-content2"><p>Content...</p></div>'+
                '</div>',

            upcast: function( element ) {
                return element.name == 'div' && element.hasClass( 'nf-columns' );
            }
        } );
    }
});
