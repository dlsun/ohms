/*
 *  This Source Code Form is subject to the terms of the Mozilla Public
 *  License, v. 2.0. If a copy of the MPL was not distributed with this
 *  file, You can obtain one at http://mozilla.org/MPL/2.0/.
 *
 *  Copyright (c) 2013, Dennis Sun <dlsun@stanford.edu>
 */

var OHMS = (function(OHMS) {
	
	var Homework = function () {
	    this.questions = [];
	    this.load_homework();
	}

	Homework.prototype.load_homework = function () {

	    var questions = $(".question");
	    for (var i=0; i<questions.length; i++) {
		var question = new OHMS.Question(this,questions.eq(i));
		this.questions.push(question);
	    }
	}

	OHMS.Homework = Homework;

	return OHMS;

    }(OHMS));