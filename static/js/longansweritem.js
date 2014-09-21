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
	this.preview = this.element.find(".preview");
	this.bind_events();
    }
    
    LongAnswerItem.prototype = new OHMS.Item();
    
    LongAnswerItem.prototype.bind_events = function () {
	var that = this;
	this.textarea.keyup(function(event) {
	    that.preview.text(event.target.value);
	    MathJax.Hub.Typeset(that.preview.get(0));
	})
	this.textarea.autosize();
    }
    
    LongAnswerItem.prototype.get_value = function () {
	return this.textarea.val();
    }

    LongAnswerItem.prototype.set_value = function (value) {
	this.textarea.val(value);
	this.preview.text(value);
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
