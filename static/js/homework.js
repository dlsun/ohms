/*
 *  This Source Code Form is subject to the terms of the Mozilla Public
 *  License, v. 2.0. If a copy of the MPL was not distributed with this
 *  file, You can obtain one at http://mozilla.org/MPL/2.0/.
 *
 *  Copyright (c) 2013, OHMS Development Team
 */

var OHMS = (function(OHMS) {
	
    var Homework = function () {
	this.name = "";
	this.questions = [];
	this.load_homework();
	this.bind_events();
    }

    Homework.prototype.bind_events = function () {
	$("#homeworkNameAdmin").change(function() {
	    this.update_name($("#homeworkNameAdmin").val());
	});
    }
    
    Homework.prototype.load_homework = function () {

	this.id = $("#homeworkID").val();
	this.name = $("#homeworkName").val();
	var questions = $(".question");
	for (var i=0; i<questions.length; i++) {
	    var question = new OHMS.Question(this,questions.eq(i));
	    this.questions.push(question);
	}
    }

    Homework.prototype.update_name = function(name) {
	this.name = name;
	$.ajax({
	    url : "update_hw_name",
	    type : "POST",
	    dataType : "json",
	    data : {
		hw_id: this.id,
		hw_name: this.name,
	    }
	})
    }
    
    OHMS.Homework = Homework;
    
    return OHMS;
    
}(OHMS));
