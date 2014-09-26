$(".submit").click(function () {
  var div = $(this).parents(".grading").eq(0);
  var response_id = div.attr("id");
  var score = div.find("input").val();
  var comments = div.find("textarea").val();
  $.ajax({
    url : "update_response",
    type : "POST",
    dataType : "text",
    data : {
      response_id: response_id,
      score: score,
      comments: comments
    },
    success : function (data) {
      div.find(".score").text(score);
      div.find(".comments").text(comments);
      div.css("background-color", "#dff0d8");
    },
    error : function () {
      add_alert("Your update was not recorded successfully.");
    }
  })
})
