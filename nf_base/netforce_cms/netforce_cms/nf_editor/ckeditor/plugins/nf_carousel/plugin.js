CKEDITOR.plugins.add('nf_carousel', {
    requires: 'widget',
    icons: 'nf_carousel',

    init: function( editor ) {
        editor.widgets.add( 'nf_carousel', {
            editables: {
                content1: {
                    selector: '.nf-carousel-content1',
                },
                content2: {
                    selector: '.nf-carousel-content2',
                },
                content3: {
                    selector: '.nf-carousel-content3',
                },
            },

            template:
                '<div class="nf-carousel">'+
                '<div class="carousel slide" data-ride="carousel">'+
                  '<ol class="carousel-indicators">'+
                    '<li data-target="#carousel-example-generic" data-slide-to="0" class="active"></li>'+
                    '<li data-target="#carousel-example-generic" data-slide-to="1"></li>'+
                    '<li data-target="#carousel-example-generic" data-slide-to="2"></li>'+
                  '</ol>'+
                  '<div class="carousel-inner">'+
                    '<div class="item active">'+
                      '<img src="http://placehold.it/1200x300&text=First Slide" alt="First slide">'+
                      '<div class="carousel-caption nf-carousel-content1">'+
                        'Content1...'+
                      '</div>'+
                    '</div>'+
                    '<div class="item">'+
                      '<img src="http://placehold.it/1200x300&text=Second Slide" alt=Second slide">'+
                      '<div class="carousel-caption nf-carousel-content2">'+
                        'Content2...'+
                      '</div>'+
                    '</div>'+
                    '<div class="item">'+
                      '<img src="http://placehold.it/1200x300&text=Third Slide" alt=Third slide">'+
                      '<div class="carousel-caption nf-carousel-content3">'+
                        'Content3...'+
                      '</div>'+
                    '</div>'+
                  '</div>'+
                  '<a class="left carousel-control" href="#carousel-example-generic" data-slide="prev">'+
                    '<span class="glyphicon glyphicon-chevron-left"></span>'+
                  '</a>'+
                  '<a class="right carousel-control" href="#carousel-example-generic" data-slide="next">'+
                    '<span class="glyphicon glyphicon-chevron-right"></span>'+
                  '</a>'+
                '</div>'+
                '</div>',

            upcast: function( element ) {
                return element.name == 'div' && element.hasClass( 'nf-carousel' );
            }
        } );
    }
});
