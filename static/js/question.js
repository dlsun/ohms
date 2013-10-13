/*
 *  This Source Code Form is subject to the terms of the Mozilla Public
 *  License, v. 2.0. If a copy of the MPL was not distributed with this
 *  file, You can obtain one at http://mozilla.org/MPL/2.0/.
 *
 *  Copyright (c) 2013, OHMS Development Team
 */

var OHMS = (function(OHMS) {
	
	var Question = function (homework,question) {
	    this.element = question;
	    this.homework = homework;
	    this.id = this.element.attr("id");
	    this.points = parseFloat(this.element.attr("points"));

	    this.items = [];
	    var item_elements = this.element.find(".item");
	    for(var i=0; i<item_elements.length; i++) {
		var item_element = item_elements.eq(i);
		var type = item_element.attr("itemtype");
		if (type == "multiple-choice") {
		    var item = new OHMS.MultipleChoiceItem(this,item_element);
		} else if (type == "short-answer") {
		    var item = new OHMS.ShortAnswerItem(this,item_element);
		} else if (type == "long-answer") {
		    var item = new OHMS.LongAnswerItem(this,item_element);
		}
		this.items.push(item);
	    }

	    this.load_response();
	    this.bind_events();
	}

	Question.prototype.bind_events = function () {
	    var that = this;
	    // submit onclick handler
	    this.element.find(".submit").click(function () {
		    that.lock();
		    that.submit_response();
		})
	}

	Question.prototype.load_response = function () {
	    $.ajax({
		    url : "load?q_id=" + this.id,
		    type : "GET",
		    dataType : "json",
		    success : $.proxy(this.load_response_success,this),
		    error : $.proxy(this.load_response_error,this),
		});
	}

	Question.prototype.load_response_success = function (data) {
	    if (data.submission) {
		for (var i=0; i<this.items.length; i++) {
		    this.items[i].set_value(data.submission.item_responses[i].response);
		}
		this.update(data);
	    }
	    if (!data.locked)
		this.unlock();
	    if (data.solution)
		for (var i=0; i<data.solution.length; i++) {
		    this.items[i].set_solution(data.solution[i]);
		}
	    MathJax.Hub.Typeset(this.element)
	}

	Question.prototype.load_response_error = function (xhr) {
	    console.log(xhr.responseText);
	}

	Question.prototype.submit_response = function () {
	    var that = this;
	    var data = new FormData();
	    for (var i=0; i<this.items.length; i++) {
		if (this.items[i].get_value() == undefined) {
		    alert("You must make a selection for all multiple choice questions.");
		    that.unlock();
		    return false;
		}
		data.append("responses",this.items[i].get_value());
	    }
	    var req = new XMLHttpRequest();
	    req.open("POST","submit?q_id=" + this.id,true);
	    req.onload = function (event) {
		if(event.target.status === 200) {
		    data = JSON.parse(event.target.response);
		    $.proxy(that.submit_response_success,that)(data);
		} else {
		    $.proxy(that.submit_response_error,that)(event.target);
		}
	    }
	    req.onerror = this.submit_response_error;
	    req.send(data);
	}

	Question.prototype.submit_response_success = function (data) {
	    this.update(data);
	    if (!data.locked)
		this.unlock();
	}

	Question.prototype.submit_response_error = function (xhr) {
	    this.unlock();
	    console.log(xhr.responseText);
	}

	Question.prototype.lock = function () {
	    for (var i=0; i<this.items.length; i++) {
		this.items[i].lock();
	    }
	    this.element.find(".submit").attr('disabled','disabled');	    
	}

	Question.prototype.unlock = function () {
	    for (var i=0; i<this.items.length; i++) {
		this.items[i].unlock();
	    }
	    this.element.find(".submit").removeAttr('disabled');
	}

	Question.prototype.update = function (data) {

	    // update score
	    var score = data.submission.score;
	    var score_element = this.element.find(".score");
	    if (score === this.points) {
		score_element.html("<img src='/class/stats60/static/img/checkmark.png' " + 
				   "height='30' width='26'> " + 
				   "Congrats! You've earned all " + 
				   this.points + " points.");
		score_element.attr("class","score alert alert-success");
	    } else if (score == null) {
		score_element.html("SCORE PENDING");
		score_element.attr("class","score alert-info");
	    } else {
		score_element.html("<strong>You have earned " + score + 
			   " out of " + this.points + 
			   " points.</strong>");
		score_element.attr("class","score alert alert-error");
	    }

	    // update comments
	    this.element.find(".comments").html(data.submission.comments);

	    // update time
	    this.element.find(".time").html("Last submission at " +
					    data.submission.time + " PDT");
	}

	OHMS.Question = Question;

	return OHMS;

    }(OHMS));
