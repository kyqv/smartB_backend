CKEDITOR.plugins.add('nf_jumbotron', {
    requires: 'widget',
    icons: 'nf_jumbotron',

    init: function( editor ) {
        editor.widgets.add( 'nf_jumbotron', {
            editables: {
                content: {
                    selector: '.nf-jumbotron-content',
                }
            },

            template:
                '<div class="jumbotron nf-jumbotron">'+
                '<div class="nf-jumbotron-content">'+
                '<h1>Hello World!</h1>'+
                '<p>This is a simple hero unit, a simple jumbotron-style component for calling extra attention to featured content or information.</p>'+
                '<button class="btn btn-primary">Learn more</button>'+
                '</div>'+
                '</div>',

            upcast: function( element ) {
                return element.name == 'div' && element.hasClass( 'nf-jumbotron' );
            }
        } );
    }
});
