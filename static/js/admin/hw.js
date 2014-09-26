var cm = CodeMirror.fromTextArea($("textarea#xml_code").get(0), {
    lineNumbers: true
});

$("button#add_question").click( function () {
    $.ajax({
	url : "add_question",
	type : "POST",
	dataType : "text",
	data : {
	    hw_id : $("input:hidden[name=hw_id]").val(),
	    xml : cm.getDoc().getValue()
	},
	success : function (data) {
	    alert("Question added successfully! Please refresh the page.");
	},
	error : function (xhr) {
	    add_alert("The update failed because:<br> " + xhr.responseText);
	}
    })
})

function get_form_elements () {
    var form = $("div#peer_review_form").eq(0);
    return {
        question_id: form.find("select[name=question_id]").val(),
        n_reviews: parseInt(form.find("input[name=n_reviews]").val()),
        peer_points: parseFloat(form.find("input[name=peer_points]").val()),
        is_self: form.find("input[name=self]").attr("checked"),
        self_points: parseFloat(form.find("input[name=self_points]").val()),
        rate_points: parseFloat(form.find("input[name=rate_points]").val()),
    }
}

function calculate_total () {
    var form = get_form_elements();
    var total = form["peer_points"] * form["n_reviews"];
    if (form["is_self"]) total += form["self_points"];
    total += form["rate_points"];
    return $("input[name=total_points]").val(total);
}

calculate_total();

$(".formelt").change( calculate_total );

$("#add_peer_review").click( function () {
    var form = get_form_elements();
    var xml = "<question review='true' question_id='" + form["question_id"] + "'>\n";
    for (var i=1; i<=form["n_reviews"]; i++)
	xml += "  <peer points='" + form["peer_points"] + "' />\n";
    if (form["is_self"])
	xml += "  <self points='" + form["self_points"] + "' />\n";
    xml += "  <rate points='" + form["rate_points"] + "' />\n";
    xml += "</question>";
    cm.getDoc().setValue(xml);
})
