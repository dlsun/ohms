/*
 *  This Source Code Form is subject to the terms of the Mozilla Public
 *  License, v. 2.0. If a copy of the MPL was not distributed with this
 *  file, You can obtain one at http://mozilla.org/MPL/2.0/.
 *
 *  Copyright (c) 2012-2013, Dennis Sun <dlsun@stanford.edu>
 */


var OHMS = (function(OHMS) {
	
	var LongAnswerItem = function (question,item) {
	    OHMS.Item.apply(this,arguments);
	}

	LongAnswerItem.prototype = new OHMS.Item();

	LongAnswerItem.prototype.set_solution = function (solution) {
	    this.element.after("<div class='alert alert-success'>" + solution + "</div>");
	}

	OHMS.LongAnswerItem = LongAnswerItem;

	return OHMS;

    }(OHMS));
