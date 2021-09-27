let team1 = document.getElementById("team_one")
let team2 = document.getElementById("team_two")
let team3 = document.getElementById("team_three")
let team4 = document.getElementById("team_four")
let team5 = document.getElementById("team_five")
let team6 = document.getElementById("team_six")
let team7 = document.getElementById("team_seven")
let team8 = document.getElementById("team_eight")
let team9 = document.getElementById("team_nine")
let team10 = document.getElementById("team_ten")
let team11 = document.getElementById("team_eleven")
let team12 = document.getElementById("team_twelve")

fetch("/apis/all_members?active=1").then(function(response){
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
        team1.innerHTML = optionHTML;
        team2.innerHTML = optionHTML;
        team3.innerHTML = optionHTML;
        team4.innerHTML = optionHTML;
        team5.innerHTML = optionHTML;
        team6.innerHTML = optionHTML;
        team7.innerHTML = optionHTML;
        team8.innerHTML = optionHTML;
        team9.innerHTML = optionHTML;
        team10.innerHTML = optionHTML;
        team11.innerHTML = optionHTML;
        team12.innerHTML = optionHTML;
        
    })
})