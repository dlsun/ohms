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
	    // allow editable source code for admins
	    var editable = this.element.find(".editable");
	    editable.dblclick(function () {
		editable.hide();
		var source = that.element.find(".source");
		source.show();
		var editor = CodeMirror.fromTextArea(source[0], {
		    lineNumbers: true
		    });
		editor.on("blur", function () {
		    $.ajax({
			url : "update_question",
			type : "POST",
			dataType : "json",
			data : {
			    q_id: that.id,
			    xml: editor.getDoc().getValue(),
			}, 
			success : function (data) {
			    // return editor to textarea, then hide
			    editor.toTextArea();
			    source.hide();
			    // show the original question and render MathJax
			    editable.html(data.html).show();
			    MathJax.Hub.Typeset(that.element.get(0));
			}, 
			error : function (xhr) {
			    add_alert("The update failed because <br><br>" + xhr.responseText);
			}
		    });
		});
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
		this.update(data.submission);
	    }
	    if (!data.locked)
		this.unlock();
	    if (data.solution)
		for (var i=0; i<data.solution.length; i++) {
		    this.items[i].set_solution(data.solution[i]);
		}
	    MathJax.Hub.Typeset(this.element.get(0));
	}

	Question.prototype.load_response_error = function (xhr) {
	    if(xhr.responseText)
		add_alert(xhr.responseText);
	    else
		add_alert("Unknown error");
	}

	Question.prototype.submit_response = function () {
	    var that = this;
	    var data = new FormData();
	    for (var i=0; i<this.items.length; i++) {
		if (this.items[i].get_value() == undefined || this.items[i].get_value() == "") {
		    add_alert("You must answer all parts of the question before submitting.");
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
	    this.update(data.submission);
	    if (!data.locked)
		this.unlock();
	}

	Question.prototype.submit_response_error = function (xhr) {
	    this.unlock();
	    if(xhr.responseText)
		add_alert(xhr.responseText);
	    else
		add_alert("Unknown error");
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

	Question.prototype.update = function (submission) {

	    // update score
	    var score = submission.score;
	    var score_element = this.element.find(".score");
	    if (score === this.points) {
		score_element.html("<img src='/class/psych10/static/img/checkmark.png' " + 
				   "height='30' width='26'> " + 
				   "Congrats! You've earned all " + 
				   this.points + " points.");
		score_element.attr("class","score alert alert-success");
	    } else if (score != null) {
		score_element.html("<strong>You have earned " + score + 
			   " out of " + this.points + 
			   " points.</strong>");
		score_element.attr("class","score alert alert-error");
	    } else {
		score_element.html("<strong>This problem is worth " + this.points + " points.</strong>");
		score_element.attr("class","score");
	    }

	    // update comments
	    var comment_elements = this.element.find(".comments");
	    var comments = submission.comments;
	    if (comments instanceof Array) {
		for (var i=0; i<comments.length; i++) {
		    comment_elements.eq(i).html(comments[i]);
		}
	    } else {
		comment_elements.html(comments);
	    }

	    // update time
	    if (submission.time) {
		this.element.find(".time").html("Last submission at " +
						submission.time + " PDT");
	    }
	}

	OHMS.Question = Question;

	return OHMS;

    }(OHMS));
