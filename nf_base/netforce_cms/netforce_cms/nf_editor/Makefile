all: build/nf_editor.min.js build/nf_editor.min.css

build/templates.js: templates/*.hbs
	handlebars -e hbs -f $@ $^

build/nf_editor.min.js: lib/jquery.js lib/underscore.js lib/backbone.js lib/handlebars.js build/templates.js views/editor_bar.js nf_editor.js
	cat $^ > $@

build/nf_editor.min.css: css/nf_editor.css
	cat $^ > $@

clean:
	rm -f build/*
