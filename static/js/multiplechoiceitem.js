/*
 *  This Source Code Form is subject to the terms of the Mozilla Public
 *  License, v. 2.0. If a copy of the MPL was not distributed with this
 *  file, You can obtain one at http://mozilla.org/MPL/2.0/.
 *
 *  Copyright (c) 2012-2013, Dennis Sun <dlsun@stanford.edu>
 */


var OHMS = (function(OHMS) {
	
	var MultipleChoiceItem = function (question,item) {
	    OHMS.Item.apply(this,arguments);
	}

	MultipleChoiceItem.prototype = new OHMS.Item();

	MultipleChoiceItem.prototype.get_value = function () {
	    return this.element.find(":checked").val();
	}

	MultipleChoiceItem.prototype.set_value = function (value) {
	    this.element.find("[value="+value+"]").attr("checked","checked");
	}

	MultipleChoiceItem.prototype.unlock = function () {
	    this.element.find("input").removeAttr("disabled");
	}

	MultipleChoiceItem.prototype.lock = function () {
	    this.element.find("input").attr("disabled","disabled");
	}

	MultipleChoiceItem.prototype.set_solution = function (solution) {
	    this.element.find("[value="+solution+"]").parent().addClass("alert-success");
	}

	
	OHMS.MultipleChoiceItem = MultipleChoiceItem;

	return OHMS;

    }(OHMS));
