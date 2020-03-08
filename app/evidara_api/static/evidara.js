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
  let response = fetch("api/v1/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(queryMessage)
  })
    .then(response => response.json())
    .then(data => {
      console.log("Success:", data);
    });
};

destroyCard = function(cardButton) {
  let parentCard = cardButton.closest(".query-parameter-card");
  while (parentCard.firstChild) {
    parentCard.firstChild.remove();
  }
  parentCard.remove();
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
  let firstChoice = document.createElement("option");
  firstChoice.setAttribute("value", 0);
  firstChoice.appendChild(document.createTextNode("Select a node type"));
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
