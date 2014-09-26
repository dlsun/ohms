$(".update").click(function(event) {
  var row = $(this).parents("tr").eq(0);
  $.ajax({
    url : "update_due_date",
    type : "POST",
    dataType : "text",
    data : {
      hw_id: row.attr("value"),
      start_date: row.find("input[name='start_date']").val(),
      due_date: row.find("input[name='due_date']").val()
    },
    success : function (data) {
      alert("Your update was successful! Please refresh the page.");
    },
    error : function () {
      alert("Your update was not successful. Please try again");
    }
  })
})

$(".add").click(function (event) {
  var row = $(this).parents("tr").eq(0);
  $.ajax({
    url : "add_homework",
    type : "POST",
    dataType : "text",
    data : {
      name: row.find("input[name='name']").val(),
      start_date: row.find("input[name='start_date']").val(),
      due_date: row.find("input[name='due_date']").val()
    },
    success : function (data) {
      alert("Homework successfully added! Please refresh the page.");
    },
    error : function () {
      alert("Homework was not added. Please try again");
    }
  })
})
