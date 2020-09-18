//
// Globals
//
const curieExamples = {
  "biolink:Gene": "e.g. ENTREZ:59272",
  "biolink:BiologicalProcess": "e.g. GO:0045833",
  "biolink:MolecularActivity": "e.g. GO:0003884",
  "biolink:ChemicalSubstance": "e.g. DB08991",
  "biolink:CellularComponent": "e.g. GO:0005759",
  "biolink:Pathway": "e.g. PC7_2621",
  "biolink:Disease": "e.g. DOID:4606",
  "biolink:GrossAnatomicalStructure": "e.g. UBERON:0002352",
  "biolink:Protein": "e.g. UNIPROT:A0A023HHK9",
  "0": "CURIEs ignored"
};

var currentResults = Object(); //hold query results later

//
// Query Handlers
//

getNodes = function() {
  let nodes = [];
  let userInput = document.getElementsByClassName("card-body");
  for (x = 0; x < userInput.length; x++) {
    nodes.push({
      node_id: "n" + x,
      curie: userInput[x].getElementsByClassName("node-curie")[0].value,
      type: userInput[x].getElementsByClassName("node-type-selector")[0].value
    });
  }
  return nodes;
};

getEdges = function(nodes) {
  let edges = [];
  for (x = 0; x < nodes.length; x++) {
    if (nodes[x].node_id !== "n0") {
      edges.push({
        edge_id: "e" + (x - 1),
        source_id: nodes[x - 1].node_id,
        target_id: nodes[x].node_id
      });
    }
  }
  return edges;
};

getAlgoritmParameters = function() {
  let extraParams = {};
  if (document.getElementById("psev").checked) {
    extraParams["psev-context"] = document.getElementById("psev-term").value;
  }
  if (document.getElementById("evidentiary").checked) {
    document.getElementsByName("evidence-algorithm").forEach(element => {
      if (element.checked) {
        if (element.value === "select-cohort") {
          extraParams["evidentiary"] = document.getElementById("cohort").value;
        } else {
          extraParams["evidentiary"] = document.getElementById(
            "auto-find"
          ).value;
        }
      }
    });
  }
  return extraParams;
};

getUniqueEdges = function(queryResults) {
  const allEdges = queryResults["results"]
    .map(x => x["result_graph"]["edges"])
    .flat();
  const uniqueEdges = {};
  allEdges.forEach(function(edge) {
    // update keys for d3 viz
    (edge["source"] = edge["source_id"]), (edge["target"] = edge["target_id"]);
    uniqueEdges[edge.id] = edge;
  });
  return Object.values(uniqueEdges);
};

getUniqueNodes = function(queryResults) {
  const allNodes = queryResults["results"]
    .map(x => x["result_graph"]["nodes"])
    .flat();
  const uniqueNodes = {};
  allNodes.forEach(node => (uniqueNodes[node.id] = node));
  return Object.values(uniqueNodes);
};

spinnerHandler = function(action) {
  if (action === "create") {
    console.log("disabling button; adding spinner");

    const queryButton = document.getElementById("queryButton");
    queryButton.setAttribute("disabled", true);

    const spinner = document.createElement("span");
    spinner.className = "spinner-border spinner-border-sm ml-2";
    spinner.setAttribute("role", "status");
    spinner.setAttribute("aria-hidden", "true");
    spinner.id = "querySpinner";

    queryButton.textContent = "Searching..";
    queryButton.appendChild(spinner);
  } else if (action === "destroy") {
    const queryButton = document.getElementById("queryButton");
    queryButton.textContent = "Submit Query";
    queryButton.removeAttribute("disabled");
  }
};

resultsTextHandler = function(results) {
  const resultsDiv = document.getElementById("text-results");
  resultsDiv.innerHTML = "";
  const textResults = document.createElement("p");
  textResults.appendChild(
    document.createTextNode(
      "Query finished!  " + results["results"].length + " results"
    )
  );
  resultsDiv.append(textResults);
};

query = function() {
  let nodesArray = getNodes();
  let edgesArray = getEdges(nodesArray);
  let queryMessage = {
    query_message: {
      query_graph: {
        nodes: nodesArray,
        edges: edgesArray
      },
      query_options: getAlgoritmParameters()
    }
  };
  spinnerHandler("create");
  fetch("api/v1/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(queryMessage)
  })
    .then(response => response.json())
    .then(data => {
      currentResults = data;
      resultsTextHandler(currentResults);
      visSetup();
      let graphData = {
        nodes: getUniqueNodes(currentResults),
        edges: getUniqueEdges(currentResults)
      };
      render(graphData);
      resultsToTable(data.results);
      spinnerHandler("destroy");
    })
    .catch(error => {
      console.warn(error);
      const resultsDiv = document.getElementById("text-results");
      resultsDiv.innerHTML = ""
      const resultsText = document.createElement("p")
      resultsText.appendChild(document.createTextNode("query error!"))
      resultsDiv.appendChild(resultsText)
      spinnerHandler("destroy");
    });
};

//
// DOM Modifiers and Supporters
//

getNodeTypes = function() {
  // this could just be a post request to the api, which should presumably have a
  // supported "get_valid_nodes" endpoint
  let nodeTypes = [];
  let startNodeSelector = document.getElementById("start-node-type");
  for (x = 0; x < startNodeSelector.length; x++) {
    if (startNodeSelector[x].value !== "0") {
      nodeTypes.push(startNodeSelector[x].value);
    }
  }
  return nodeTypes;
};

destroyCard = function(cardButton) {
  let parentCard = cardButton.closest(".query-parameter-card");
  while (parentCard.firstChild) {
    parentCard.firstChild.remove();
  }
  parentCard.remove();
};

updateCuriePlaceholder = function(selector) {
  selector.previousElementSibling.setAttribute(
    "placeholder",
    curieExamples[selector.value]
  );
};

add_node_selector = function() {
  // body container
  let newCardBody = document.createElement("div");
  newCardBody.className = "card-body";
  // title and destroy button
  let cardTitleRow = document.createElement("div");
  cardTitleRow.className = "row justify-content-center";
  let cardTitleCol = document.createElement("div");
  cardTitleCol.className = "col-8 offset-1";
  let innerA = document.createElement("a");
  innerA.appendChild(document.createTextNode("intermediate node"));
  let innerh5 = document.createElement("h5");
  innerh5.className = "card-title text-center";
  let removeButton = document.createElement("button");
  removeButton.setAttribute("onclick", "destroyCard(this);");
  removeButton.appendChild(document.createTextNode("X"));
  removeButton.className = "btn btn-light btn-sm destroy-button";
  let removeContainer = document.createElement("div");
  removeContainer.className = "col-1";
  removeContainer.appendChild(removeButton);
  innerh5.appendChild(innerA);
  cardTitleCol.appendChild(innerh5);
  cardTitleRow.appendChild(cardTitleCol);
  cardTitleRow.appendChild(removeContainer);
  newCardBody.appendChild(cardTitleRow);
  // search header and box
  newCardBody
    .appendChild(document.createElement("h6"))
    .appendChild(document.createTextNode("Search CURIE"));
  let newInput = document.createElement("input");
  newInput.className = "node-curie";
  newInput.setAttribute("placeholder", "e.g. ENTREZ:59272");
  newCardBody.appendChild(newInput);
  // select menu
  let newSelect = document.createElement("select");
  newSelect.className = "node-type-selector";
  newSelect.setAttribute("onchange", "updateCuriePlaceholder(this);");
  let firstChoice = document.createElement("option");
  firstChoice.setAttribute("value", 0);
  firstChoice.appendChild(document.createTextNode("Any"));
  newSelect.appendChild(firstChoice);
  newCardBody.appendChild(newSelect);
  //now get the other select menu and iterate through its node types
  getNodeTypes().forEach(nodeType => {
    let newOption = document.createElement("option");
    newOption.setAttribute("value", nodeType);
    newOption.appendChild(document.createTextNode(nodeType));
    newSelect.appendChild(newOption);
  });
  // outermost container
  let newNode = document.createElement("div");
  newNode.className = "query-parameter-card col-lg-3 col-md-12 col-sm-12";
  let cardContainer = document.createElement("div");
  cardContainer.className = "card h-100";
  cardContainer.appendChild(newCardBody);
  newNode.appendChild(cardContainer);
  //shove it in
  let endNode = document.getElementById("node-adder");
  endNode.parentNode.insertBefore(newNode, endNode);
};

visSetup = function() {
  let mc = document.getElementById("main-content");
  if (!document.getElementById("graph-container")) {
    let graphRow = document.createElement("div");
    graphRow.className = "row justify-content-center";
    graphRow.id = "graph-row";
    let graphCol = document.createElement("div");
    graphCol.className = "col-12 text-center";
    graphCol.id = "graph-container";
    // make a horizontal divider
    const horizontalLineContainer = document.createElement("div");
    horizontalLineContainer.setAttribute("class", "col-12");
    const horizontalLine = document.createElement("hr");
    horizontalLineContainer.appendChild(horizontalLine);
    graphRow.appendChild(horizontalLineContainer);
    graphRow.appendChild(graphCol);
    mc.appendChild(graphRow);
  } else {
    const graphContainer = document.getElementById("graph-container");
    while (graphContainer.firstChild) {
      graphContainer.firstChild.remove();
    }
  }

  setup(); // actual d3 params from evidara-graph.js
};

// add a table

getLongestArrayLength = function(result) {
  const maxLengths = Array(
    result.result_graph.nodes.map(x => x.node_attributes.length),
    result.result_graph.edges.map(x => x.edge_attributes.length)
  ).flat();
  return Math.max(...maxLengths);
};

resultsToTable = function(results) {
  var existingTable = document.getElementById("resultsTable");
  if (!existingTable) {
    // make the table if doesn't exist yet
    const resultsTableRow = document.createElement("div");
    resultsTableRow.setAttribute("class", "row justify-content-center");
    const resultsTableCol = document.createElement("div");
    resultsTableCol.setAttribute("class", "col-12 table-responsive");
    const resultsTable = document.createElement("table");
    resultsTable.setAttribute("id", "resultsTable");
    resultsTable.setAttribute(
      "class",
      "table table-bordered table-sm evidara-table"
    );
    // divider
    const horizontalLineContainer = document.createElement("div");
    horizontalLineContainer.setAttribute("class", "col-12");
    const horizontalLine = document.createElement("hr");
    horizontalLineContainer.appendChild(horizontalLine);

    // text
    const resultsTitleTextContainer = document.createElement("div");
    resultsTitleTextContainer.setAttribute("class", "col-4 text-center");
    const resultsTitleText = document.createElement("h4");
    resultsTitleText.appendChild(
      document.createTextNode("Result Knowlege Graphs")
    );
    const resultsTitleSubtext = document.createElement("p");
    resultsTitleSubtext.appendChild(
      document.createTextNode("note: this table scrolls horizontally")
    );
    resultsTitleTextContainer.appendChild(resultsTitleText);
    resultsTitleTextContainer.appendChild(resultsTitleSubtext);
    // append them up
    const mainContent = document.getElementById("main-content");
    resultsTableCol.appendChild(resultsTable);
    resultsTableRow.appendChild(horizontalLineContainer);
    resultsTableRow.appendChild(resultsTitleTextContainer);
    resultsTableRow.appendChild(resultsTableCol);
    mainContent.appendChild(resultsTableRow);
  } else {
    // delete all the table content if it's there
    while (existingTable.firstChild) {
      existingTable.firstChild.remove();
    }
  }
  if (!results[0]) {
    return;
  }
  // grab the table upon creation or after deletion of content and
  // start populating the table with data
  var existingTable = document.getElementById("resultsTable");
  // number of columns we'll need... do we even need this?
  const queryLength = document.getElementsByClassName("card-body").length;
  console.log(results);
  // header
  const thead = existingTable.createTHead();
  const headerRow = thead.insertRow();
  const rank = document.createElement("th");
  rank.appendChild(document.createTextNode("Result Rank"));
  const score = document.createElement("th");
  if (results[0].score_name) {
    score.appendChild(document.createTextNode(results[0].score_name));
  } else {
    score.appendChild(document.createTextNode("Score"));
  }

  headerRow.appendChild(rank);
  headerRow.appendChild(score);

  for (i = 0; i < queryLength; i++) {
    let node = document.createElement("th");
    node.appendChild(document.createTextNode("n" + i));
    node.setAttribute("colspan", 2);
    headerRow.appendChild(node);
    if (i !== queryLength - 1) {
      let edge = document.createElement("th");
      edge.appendChild(document.createTextNode("e" + i));
      edge.setAttribute("colspan", 2);
      headerRow.appendChild(edge);
    }
  }

  // now onto the data
  for (const [index, element] of results.entries()) {
    // get cell background styling
    let row_class;
    if (index % 2 == 0) {
      row_class = "row-even";
    } else {
      row_class = "row-odd";
    }
    // get the number of rows this result will use
    maxAttributeCount = getLongestArrayLength(element);
    // create row, cells with the ranks, score, and node/edge ids
    let topRow = existingTable.insertRow();
    topRow.setAttribute("class", row_class);
    let rankCell = topRow.insertCell();
    rankCell.appendChild(document.createTextNode(index + 1));
    rankCell.setAttribute("rowspan", maxAttributeCount + 3);
    rankCell.setAttribute("class", "cell-sub-head");
    let scoreCell = topRow.insertCell();
    scoreCell.appendChild(document.createTextNode(element.score));
    scoreCell.setAttribute("rowspan", maxAttributeCount + 3);
    scoreCell.setAttribute("class", "cell-sub-head");
    // now we put the actual ids
    for (i = 0; i < queryLength; i++) {
      let nodeCell = topRow.insertCell();
      nodeCell.appendChild(
        document.createTextNode(element.result_graph.nodes[i].id)
      );
      nodeCell.setAttribute("colspan", 2);
      nodeCell.setAttribute("class", "cell-sub-head");
      topRow.appendChild(nodeCell);
      if (i != queryLength - 1) {
        let edgeCell = topRow.insertCell();
        edgeCell.appendChild(
          document.createTextNode(element.result_graph.edges[i].id)
        );
        edgeCell.setAttribute("colspan", 2);
        edgeCell.setAttribute("class", row_class + "-edge cell-sub-head");
        topRow.appendChild(edgeCell);
      }
    }
    // now start making attribute rows
    // make the a header row first
    createAttributeHeaderRows(existingTable, queryLength, row_class, element);
    // now the attributes

    for (i = 0; i < maxAttributeCount; i++) {
      let attribute_row = existingTable.insertRow();
      attribute_row.setAttribute("class", row_class);
      for (j = 0; j < queryLength; j++) {
        // node first
        if (element.result_graph.nodes[j].node_attributes[i]) {
          createRowCell(
            attribute_row,
            element.result_graph.nodes[j].node_attributes[i].type
          );
          createRowCell(
            attribute_row,
            element.result_graph.nodes[j].node_attributes[i].value
          );
        } else {
          createRowCell(attribute_row, "");
          createRowCell(attribute_row, "");
        }
        // now edge
        if (j !== queryLength - 1) {
          if (element.result_graph.edges[j].edge_attributes[i]) {
            createRowCell(
              attribute_row,
              element.result_graph.edges[j].edge_attributes[i].type,
              { class: row_class + "-edge" }
            );
            createRowCell(
              attribute_row,
              element.result_graph.edges[j].edge_attributes[i].value,
              { class: row_class + "-edge" }
            );
          } else {
            createRowCell(attribute_row, "", { class: row_class + "-edge" });
            createRowCell(attribute_row, "", { class: row_class + "-edge" });
          }
        }
      }
    }
  }
};

const createAttributeHeaderRows = function(
  table,
  queryLength,
  row_class,
  element
) {
  const attributeHeaderRow = table.insertRow();
  attributeHeaderRow.setAttribute("class", row_class);
  for (i = 0; i < queryLength; i++) {
    let cellClass;
    cellClass = { class: "cell-sub-head" };
    createRowCell(attributeHeaderRow, "Attribute Name", cellClass);
    createRowCell(attributeHeaderRow, "Attribute Value", cellClass);
    if (i !== queryLength - 1) {
      cellClass = { class: row_class + "-edge" + " cell-sub-head"};
      createRowCell(attributeHeaderRow, "Attribute Name", cellClass);
      createRowCell(attributeHeaderRow, "Attribute Value", cellClass);
    }
  }
  const elementTypesRow = table.insertRow();
  elementTypesRow.setAttribute("class", row_class);
  let cellClass, cellText;
  for (i = 0; i < queryLength; i++) {
    cellClass = {};
    cellText = element.result_graph.nodes[i].type[0];
    createRowCell(elementTypesRow, "Type", cellClass);
    createRowCell(elementTypesRow, cellText, cellClass);
    if (i !== queryLength - 1) {
      cellClass = { class: row_class + "-edge" };
      cellText = element.result_graph.edges[i].type;
      createRowCell(elementTypesRow, "Type", cellClass);
      createRowCell(elementTypesRow, cellText, cellClass);
    }
  }
};

const createRowCell = function(row, textValue, attributes = {}) {
  let rowCell = row.insertCell();
  rowCell.appendChild(document.createTextNode(textValue));
  Object.keys(attributes).forEach(attr =>
    rowCell.setAttribute(attr, attributes[attr])
  );
};
