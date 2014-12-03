var data = [["Student", "Score"]];
var assignment = "";

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

function hide_all_other_columns(i) {
    var sum = 0;
    var sum_sq = 0;
    var n = 0;
    var missing = [];
    var excused = [];
    var table = $("table#gradebook");
    var students = table.find('td:nth-child(2)').map(function() {
	return($(this).text());
    });

    // hide column that changes student status
    table.find('td:nth-child(3),th:nth-child(3)').hide();

    // hide columns starting with the Overall column
    for(var j=5; j<=table.find('tr:nth-child(1) td').size(); j++) {
        if(j !== i) {
            table.find('td:nth-child(' + j + '),th:nth-child(' + j + ')').hide();
        } else {
            assignment = table.find('th:nth-child(' + j + ')').text();
            var scores = table.find('td:nth-child(' + j + ')').map(function() {
                return $(this).attr("value");
            });
	    for(var k=1; k < students.size(); k++) {
		if(scores.get(k) == "") {
		    missing.push(students.get(k))
		} else if(scores.get(k) == "E") {
		    excused.push(students.get(k))
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
    $("div#histogram").css("height", "500px");
    $("div#missing").text("These students' scores are missing: " + missing.join(", ") + ".");
    $("div#excused").text("These students have been excused: " + excused.join(", ") + ".");
    $("div#stats").text("Mean: " + (sum / n).toFixed(2) + ", SD: " + 
                        (Math.sqrt(sum_sq / n - Math.pow(sum / n, 2))).toFixed(2));
    drawChart();
}

function update_grade () {
  var td = $(this).parent("td");
  var hw_id = td.attr("hw_id");
  var score = td.find(".grade").val();
  var is_excused = td.find(".excused").is(":checked");
  var stuid = $(this).parents("tr").attr("stuid");
  $.ajax({
    url : "update_grade",
    type : "POST",
    dataType : "text",
    data : {
      stuid: stuid,
      hw_id: hw_id,
      score: score,
      is_excused: is_excused,
    },
    success : function (data) {
      td.css("background-color", "#dff0d8");
    },
    error: function () {
      alert("The grade was not saved successfully. Please try again.");   
    }
  });
}

$("input.grade").change(update_grade);
$("input.excused").change(update_grade);

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

var gradebook = $("table#gradebook");
var letters = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+",
	       "D", "D-"]

$("table#cutoffs").find("input").change(function() {
    var cutoffs = $("table#cutoffs").find("input").map(function() {
	return(parseFloat($(this).val()));
    });
    gradebook.find(".overall").map(function() {
	$(this).prev().text("");
	var score = parseFloat($(this).attr("value"));
	if (score >= cutoffs[0]) $(this).prev().text(letters[0]);
	else if (score <= cutoffs[11]) $(this).prev().text("NP");
	else {
	    for(var i=0; i<11; i++) {
		if((cutoffs[i] > score) && (score >= cutoffs[i+1]))
		    $(this).prev().text(letters[i+1]);
	    }
	}
    })
})
