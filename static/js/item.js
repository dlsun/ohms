/*
 *  This Source Code Form is subject to the terms of the Mozilla Public
 *  License, v. 2.0. If a copy of the MPL was not distributed with this
 *  file, You can obtain one at http://mozilla.org/MPL/2.0/.
 *
 *  Copyright (c) 2012-2013, Dennis Sun <dlsun@stanford.edu>
 */

var OHMS = (function(OHMS) {

	var Item = function (question,item) {
	    this.question = question;
	    this.element = item;
	}

	Item.prototype.get_value = function () {
	    return this.element.val();
	}

	Item.prototype.set_value = function (value) {
	    this.element.val(value);
	}

	Item.prototype.unlock = function () {
	    this.element.removeAttr("disabled");
	}

	Item.prototype.lock = function () {
	    this.element.attr("disabled","disabled");
	}

	Item.prototype.set_solution = function (solution) {
	    this.set_value(solution);
	}

	OHMS.Item = Item;

	return OHMS;

    }(OHMS));