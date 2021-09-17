let week = document.getElementById("week");

fetch("/apis/power_rankings_available").then(function(response) {
    response.json().then(function(data) {
        console.log(data)
    let optionHTML = "<option value>Select a week...</option>";
    for (key in data) {
        optionHTML +=
        "<option value=" +
        key +
        ">" +
        data[key] +
        "</option>";
    }
    week.innerHTML = optionHTML
    });
});