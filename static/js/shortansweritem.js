/*
 *  This Source Code Form is subject to the terms of the Mozilla Public
 *  License, v. 2.0. If a copy of the MPL was not distributed with this
 *  file, You can obtain one at http://mozilla.org/MPL/2.0/.
 *
 *  Copyright (c) 2012-2013, Dennis Sun <dlsun@stanford.edu>
 */


var OHMS = (function(OHMS) {
	
	var ShortAnswerItem = function (question,item) {
	    OHMS.Item.apply(this,arguments);
	}

	ShortAnswerItem.prototype = new OHMS.Item();

	ShortAnswerItem.prototype.set_value = function (value) {
	    this.element.val(value);
	}

	ShortAnswerItem.prototype.set_solution = function (solution) {
	    this.element.after("<span class='alert-success'>" + solution + "</span>");
	}

	OHMS.ShortAnswerItem = ShortAnswerItem;

	return OHMS;

    }(OHMS));
