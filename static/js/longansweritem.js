/*
 *  This Source Code Form is subject to the terms of the Mozilla Public
 *  License, v. 2.0. If a copy of the MPL was not distributed with this
 *  file, You can obtain one at http://mozilla.org/MPL/2.0/.
 *
 *  Copyright (c) 2013, OHMS Development Team
 */


var OHMS = (function(OHMS) {
	
    var LongAnswerItem = function (question,item) {
	OHMS.Item.apply(this,arguments);
	this.textarea = this.element.find("textarea");
	this.preview = this.element.find(".response");
	this.id = this.textarea.attr("id");

	var that = this;
	tinymce.init({
	    selector: "textarea#" + this.id,
	    theme: "modern",
	    forced_root_block: false,
	    plugins: [
		"advlist autolink lists link image charmap hr anchor",
		"visualblocks code",
		"media nonbreaking save table contextmenu",
		"paste textcolor colorpicker textpattern"
	    ],
	    menubar: false,
	    toolbar1: "undo redo | alignleft aligncenter alignright | bullist numlist | link image media",
	    toolbar2: "bold italic underline | superscript subscript | fontsizeselect forecolor | table",
	    statusbar: false,
	    image_advtab: true,
	    setup: function(editor) {
		editor.on('init', function() {
		    that.editor = tinymce.get(that.id);
		    var doc = this.getDoc();
		    doc.body.style.fontSize = '14px';
		 })
		 editor.on('keyup', function() {
		     that.preview.html(that.editor.getContent());
		     MathJax.Hub.Typeset(that.preview.get(0));
		 })
	    }
	});
    }
    
    LongAnswerItem.prototype = new OHMS.Item();
        
    LongAnswerItem.prototype.get_value = function () {
	return this.editor.getContent();
    }

    LongAnswerItem.prototype.set_value = function (value) {
	if (value !== null) {
	    this.editor.setContent(value);
	    this.preview.html(value);
	}
    }

    LongAnswerItem.prototype.unlock = function () {
	this.textarea.removeAttr("disabled");
    }

    LongAnswerItem.prototype.lock = function () {
	this.textarea.attr("disabled","disabled");
    }


    LongAnswerItem.prototype.set_solution = function (solution) {
	this.element.after("<div class='alert alert-success'>" + solution + "</div>");
    }
    
    OHMS.LongAnswerItem = LongAnswerItem;
    
    return OHMS;
    
}(OHMS));
