// Store data
var data = [["Student", "Score"]];
var assignment = "";

// This function draws the histogram for each quiz using Google Charts.
google.load("visualization", "1", {packages:["corechart"]});
function drawChart() {
    var dataTable = google.visualization.arrayToDataTable(data);
    var range = dataTable.getColumnRange(1);

    var options = {
        title: assignment + ' Scores',
        legend: { position: 'none' },
        titleTextStyle: { fontSize: 24 },
	histogram: {
	    bucketSize: Math.max(1, Math.round(.02*(range.max - range.min))),
	},
        chartArea: {
            left: '10%',
            top: '10%',
            width: '80%',
            height: '80%'
        },
    };
    
    var chart = new google.visualization.Histogram(document.getElementById('histogram'));
    chart.draw(dataTable, options);
}

// This function hides all columns except for the ith column
function hide_all_other_columns(i) {
    var sum = 0;
    var sum_sq = 0;
    var n = 0;
    var missing = [];
    var excused = [];
    var table = $("table#gradebook");
    var students = table.find('td:nth-child(3)').map(function() {
	return($(this).text());
    });

    // hide duplicate column
    table.find('td:nth-child(2),th:nth-child(2)').hide();
    table.find('th,td').css("position", "relative");

    // hide column that changes student status
    table.find('td:nth-child(4),th:nth-child(4)').hide();

    // hide columns starting with the Overall column
    for(var j=6; j<=table.find('tr:nth-child(1) td').size(); j++) {
        if(j !== i) {
            table.find('td:nth-child(' + j + '),th:nth-child(' + j + ')').hide();
        } else {
            assignment = table.find('th:nth-child(' + j + ')').text();
            var scores = table.find('td:nth-child(' + j + ')').map(function() {
                return $(this).find("input.grade").val();
            });
	    var excuses = table.find('td:nth-child(' + j + ')').map(function() {
                return $(this).find("input.excused").is(":checked");
            });
	    for(var k=1; k < students.size(); k++) {
		if(excuses.get(k)) {
		    excused.push(students.get(k))
		} else if(scores.get(k) == "") {
		    missing.push(students.get(k))
		} else {
		    var score = parseFloat(scores.get(k));
		    data.push([students.get(k), score]);
                    n += 1;
                    sum += score;
                    sum_sq += Math.pow(score, 2);
		}
            }
        }
    }
    var n = data.length;
    var sorted = new Array(n);
    for(var i=1; i<n; i++) {
	sorted[i] = data[i][1];
    }
    sorted.sort(function(a, b) { return a-b });
    if(n % 2 == 1) {
	var median = sorted[Math.floor(n/2)];
    } else {
	var median = .5*(sorted[(n/2)-1] + sorted[(n/2)]);
    }
    $("div#histogram").css("height", "500px");
    $("div#missing").text("These students' scores are missing: " + missing.join(", ") + ".");
    $("div#excused").text("These students have been excused: " + excused.join(", ") + ".");
    $("div#stats").text("Mean: " + (sum / n).toFixed(2) + 
			", Median: " + median.toFixed(2) + 
			", SD: " + (Math.sqrt(sum_sq / n - Math.pow(sum / n, 2))).toFixed(2));
    drawChart();
}

// This function updates a student's grade for an assignment.
function update_grade (td, score) {
    var td = $(this).parent("td");
    var score = td.find("input.grade").val()
    var hw_id = td.attr("hw_id");
    var excused = td.find(".excused").is(":checked");
    var stuid = $(this).parents("tr").attr("stuid");
    $.ajax({
	url : "update_grade",
	type : "POST",
	dataType : "text",
	data : {
	    stuid: stuid,
	    hw_id: hw_id,
	    score: score,
	    excused: excused,
	},
	success : function (data) {
	    td.css("background-color", "#dff0d8");
	},
	error: function () {
	    alert("The grade was not saved successfully. Please try again.");   
	}
    });
}

// These event handlers call update_grade() above when a grade is changed.
$("input.grade").change(update_grade);
$("input.excused").change(update_grade);


// This function updates the maximum score for an assignment.
function update_max_score (td, score) {
    var td = $(this).parent("td");
    var max_score = td.find("input.max").val()
    var hw_id = td.attr("hw_id");
    $.ajax({
	url : "update_max_score",
	type : "POST",
	dataType : "text",
	data : {
	    hw_id: hw_id,
	    max_score: max_score,
	},
	success : function (data) {
	    alert(data);
	},
	error: function () {
	    alert("The maximum score was not changed successfully. Please try again.");   
	}
    });
}

// This event handler calls update_max_score() above when the max score for an assignment is changed.
$("input.max").change(update_max_score);


// Event handler that updates category names/weights/drops when button is pressed
$("#categories").find("input[type=button]").click(function () {
  var row = $(this).closest("tr");
  var id = row.attr("id");
  var name = row.find("input[name=name]").val();
  var weight = row.find("input[name=weight]").val();
  var drops = row.find("input[name=drops]").val();
  $.ajax({
    url : "update_category",
    type : "POST",
    dataType : "text",
    data : {
	id : id,
	name : name,
	weight : weight,
	drops : drops,
    },
    success : function (data) {
	alert(data);
    },
    error: function () {
	alert("Your changes were not saved successfully. Please try again.");   
    }
  });
});


// Calculate letter grades when letter grade cutoffs are changed.
var gradebook = $("table#gradebook");
var letters = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+",
	       "D", "D-"]
$("table#cutoffs").find("input").change(function() {
    var cutoffs = $("table#cutoffs").find("input").map(function() {
	return(parseFloat($(this).val()));
    });
    var counts = $("table#cutoffs tr.counts td");
    counts.text(0);
    gradebook.find(".overall").map(function() {
	$(this).prev().text("");
	var score = parseFloat($(this).find("input.grade").val());
	if (score >= cutoffs[0]) {
	    $(this).prev().text(letters[0]);
	    counts.eq(0).text(parseInt(counts.eq(0).text()) + 1);
	}
	else if (score <= cutoffs[11]) $(this).prev().text("NP");
	else {
	    for(var i=0; i<11; i++) {
		if((cutoffs[i] > score) && (score >= cutoffs[i+1])) {
		    $(this).prev().text(letters[i+1]);
		    counts.eq(i+1).text(parseInt(counts.eq(i+1).text()) + 1);
		}
	    }
	}
    })
});

// Remind user to bookmark admin page when they are about to change user.
$(".userid").click(function() {
    alert('You are about to enter the view of a student. In order to return to your own view again,' + 
	  'you must come back to this page and click on your own ID at the bottom of the page. ' +
	  "Since you will not be able to see the link to this page once you enter a student's view, " + 
	  "we recommend that you bookmark this page now by pressing " +
	  (navigator.userAgent.toLowerCase().indexOf('mac') != - 1 ? 'Command/Cmd' : 'CTRL') + 
	  ' + D.');
});
