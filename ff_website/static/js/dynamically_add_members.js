let member_one = document.getElementById("leagueMemberOne")
let member_two = document.getElementById("leagueMemberTwo")

selected_id_one = $('#leagueMemberOne').find(":selected").val();
selected_id_two = $('#leagueMemberTwo').find(":selected").val();

fetch("/apis/all_members?active=2").then(function(response){
    response.json().then(function(data) {

        let optionHTMLOne = "<option value>Please select a member...</option>";
        let optionHTMLTwo = "<option value>Please select a member...</option>";

        data.forEach(element => {
            if (element["member_id"] == selected_id_one){
                optionHTMLOne +=
                "<option selected=" +
                selected_id_one.toString() +
                " value=" +
                selected_id_one.toString() +
                ">" + 
                element["first_name"] + " " + element["last_name"] +
                "</option>";
            }
            else{
                optionHTMLOne +=
                "<option value=" +
                element["member_id"].toString() +
                ">" +
                element["first_name"] + " " + element["last_name"] +
                "</option>";
            }
            if (element["member_id"] == selected_id_two){
                optionHTMLTwo +=
                "<option selected=" +
                selected_id_two.toString() +
                " value=" +
                selected_id_two.toString() +
                ">" + 
                element["first_name"] + " " + element["last_name"] +
                "</option>";
            }
            else{
                optionHTMLTwo +=
                "<option value=" +
                element["member_id"].toString() +
                ">" +
                element["first_name"] + " " + element["last_name"] +
                "</option>";
            }
            
        })

        member_one.innerHTML = optionHTMLOne;
        member_two.innerHTML = optionHTMLTwo;
    })
})