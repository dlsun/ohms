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
