CKEDITOR.plugins.add('nf_image', {
    requires: 'widget',
    icons: 'nf_image',

    init: function( editor ) {
        editor.widgets.add( 'nf_image', {
            template:
                '<div class="nf-image">'+
                '<img src=""/>'+
                '</div>',

            upcast: function( element ) {
                return element.name == 'div' && element.hasClass( 'nf-image' );
            }
        } );
    }
});
