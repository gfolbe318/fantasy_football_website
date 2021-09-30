let teamB = document.getElementById("teamAName")
let teamA = document.getElementById("teamBName")

fetch("/apis/all_members?active=2").then(function(response){
    response.json().then(function(data){
        let optionHTML = "<option value>Please select a member...</option>";

        data.forEach(element => {
            optionHTML +=
            "<option value=" +
            element["member_id"].toString() +
            ">" +
            element["first_name"] + " " + element["last_name"] + 
            "</option>";
        })
        teamB.innerHTML = optionHTML;
        teamA.innerHTML = optionHTML;
        
    })
})