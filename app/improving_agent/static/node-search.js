makeSuggestionRow = function (suggestionTable, fieldNames, result) {
    let suggestionRow = suggestionTable.insertRow();
    for (i = 0; i < fieldNames.length; i++) {
      let newCell = suggestionRow.insertCell();
      newCell.appendChild(document.createTextNode(result[fieldNames[i]]));
    };
  }

  destroySuggestions = function() {
    const search_div = document.getElementById("results")
    var existingSuggestions = document.getElementById(search_div.id + "suggestions-list");
    if (existingSuggestions) {existingSuggestions.remove()};
  }

  makeSuggestions = function(data) {
    resultFields = ["identifier", "label", "name", "pref_name", "score"]
  
    const search_div = document.getElementById("results")
    destroySuggestions();
    suggestionBox = document.createElement("div");
    suggestionBox.setAttribute("id", search_div.id + "suggestions-list");
    suggestionBox.setAttribute("class", "suggestions-items");
  
    suggestionTable = document.createElement("table");
    suggestionTable.className = "searchResultTable"
    const tableHeader = suggestionTable.createTHead();
    const suggestionHeader = tableHeader.insertRow();
    for (i = 0; i < resultFields.length; i++) {
      let newHeader = document.createElement("th");
      newHeader.appendChild(document.createTextNode(resultFields[i]));
      suggestionHeader.appendChild(newHeader);
    };
    
    search_div.appendChild(suggestionBox)
    let results = data["results"]
    results.forEach(function(result) {makeSuggestionRow(suggestionTable, resultFields, result)});
    suggestionBox.appendChild(suggestionTable);
  }
  
  searchNodes = function() {
    const textSearch = document.getElementById('text-search').value;
    const searchParams = new URLSearchParams({
        autocomplete: document.getElementById("autocomplete-checkbox").checked,
        fuzz: document.getElementById("fuzz-checkbox").checked
    });
    if (textSearch.length < 2) {
        destroySuggestions();
      return;
    };
    let url = "text-search/" + textSearch + "?" + searchParams;

    fetch(url)
      .then(response => response.json())
      .then(function(data){makeSuggestions(data)})
      .catch((error) => {
        console.error('Error:', error);
      });
  }
  