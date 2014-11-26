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
	    bucketSize: Math.max(1, .02*(range.max - range.min)),
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
    var students = table.find('td:nth-child(1)').contents(); 
    for(var j=3; j<=table.find('tr:nth-child(1) td').size(); j++) {
        if(j !== i) {
            table.find('td:nth-child(' + j + '),th:nth-child(' + j + ')').hide();
        } else {
            assignment = table.find('th:nth-child(' + j + ')').text();
            var scores = table.find('td:nth-child(' + j + ')').map(function() {
                return $(this).attr("value");
            });
	    for(var k=0; k < scores.size(); k++) {
		if(scores.get(k) == "") {
		    missing.push(students.get(k).data)
		} else if(scores.get(k) == "E") {
		    excused.push(students.get(k).data)
		} else {
		    var score = parseFloat(scores.get(k));
		    data.push([students.get(k).data, score]);
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

$("input.grade").change(function () {
  var score = $(this).val();
  var td = $(this).parent("td");
  var hw_id = td.attr("hw_id");
  var stuid = $(this).parents("tr").attr("stuid");
  $.ajax({
    url : "update_grade",
    type : "POST",
    dataType : "text",
    data : {
      stuid: stuid,
      hw_id: hw_id,
      score: score,
    },
    success : function (data) {
      td.css("background-color", "#dff0d8");
    },
    error: function () {
      alert("The grade was not saved successfully. Please try again.");   
    }
  });
});
