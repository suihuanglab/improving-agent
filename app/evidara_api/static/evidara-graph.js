// set margins and canvas size
const margin = {
  top: 10,
  right: 10,
  bottom: 10,
  left: 10
};
const width = 600 - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

// set up canvas
let svg, link, node, g; // empty vars to update when the .chart div appears

setup = function() {
  svg = d3
    .select("#graph-container")
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .call(responsivefy);
  g = svg
    .append("g")
    .attr("transform", `translate(${margin.left}, ${margin.top})`)
    .attr("id", "everything");

  // set up selections
  link = g
    .append("g")
    .attr("class", "links")
    .selectAll("line");
  node = g
    .append("g")
    .attr("class", "nodes")
    .selectAll("circle");

  //add zoom capabilities
  var zoom_handler = d3.zoom().on("zoom", zoom_actions);
  zoom_handler(svg);
};

const spokeColors = {
  Gene: "#80B1D3",
  BiologicalProcess: "#FDB462",
  MolecularActivity: "#FFEE6F",
  ChemicalSubstance: "#BC80BD",
  CellularComponent: "#FFFFB3",
  Pathway: "#BEBADA",
  Disease: "#FB8072",
  Symptom: "#FCCDE5",
  GrossAnatomicalStructure: "#B3DE69",
  Protein: "#8DD3C7",
  Thing: "#C7B78F"
};

var simulation = d3
  .forceSimulation()
  .force(
    "link",
    d3
      .forceLink()
      .id(function(d) {
        return d.id;
      })
      .distance(100)
  )
  .force(
    "charge",
    d3
      .forceManyBody()
      .strength(-60)
      .distanceMin(50)
      .distanceMax(150)
  )
  .force(
    "collide",
    d3.forceCollide().radius(function(d) {
      return d.r;
    })
  )
  .force("center", d3.forceCenter(width / 2, height / 2));

function render(graph) {
  // first, deal with nodes
  node = node.data(graph.nodes, function(d) {
    return d.id;
  });
  // general update for nodes
  node
    .exit()
    .transition()
    .duration(100)
    .attr("r", 0)
    .remove();
  node
    .transition()
    .duration(100)
    .attr("fill", function(d) {
      return spokeColors[d.type[0]];
    });

  node = node
    .enter()
    .append("g")
    .attr("class", "circle")
    .call(
        d3
          .drag()
          .on("start", dragstarted)
          .on("drag", dragged)
        //   .on("end", dragended)
      );

  node = node.merge(node);

  node
    .append("circle")
    .attr("r", 17)//function(d){
        // if ("psev-weight" in d["node_attributes"]){
        //     return 30 * (10000 * d["node_attributes"]["psev_weight"])
        //     // maybe make this simply the index in the array.. which should map to higher
        //     // scores
        // } else {return 12}
    //})
    .attr("fill", function(d) {
      return spokeColors[d.type];
    })
    .attr("type", function(d) {
      return d.type;
    })
    .call(function(d) {
      d.transition().duration(1500);
    })
    .merge(node);

  // give all nodes a title with their id for hover identification
  node.append("title").text(function(d) {
    return d.name;
  });

  node
    .append("text")
    .text(function(d) {
      return d.name;
    })
    .style("text-anchor", "middle")
    .attr("class", "labelText");
  //now the edges
  link = link.data(graph.edges, function(d) {
    return d.source.id + "-" + d.target.id;
  });

  //   link general update pattern with attrTween to keep links connected to disappearing nodes
  link
    .exit()
    .transition()
    .duration(100)
    .attr("stroke-opacity", 0)
    .attr("stroke-width", 0)
    .attrTween("x1", function(d) {
      return function() {
        return d.source.x;
      };
    })
    .attrTween("x2", function(d) {
      return function() {
        return d.target.x;
      };
    })
    .attrTween("y1", function(d) {
      return function() {
        return d.source.y;
      };
    })
    .attrTween("y2", function(d) {
      return function() {
        return d.target.y;
      };
    })
    .remove();

  link = link
    .enter()
    .append("line")
    .call(function(link) {
      link
        .transition()
        .duration(1500)
        .attr("stroke-width", 3); //function(d) {
      //return d.value;
      //}); this was a function to set stroke width on some value.. consider doing so with correlation score
    })
    .merge(link);

  // add nodes and links to the siumlation
  simulation.nodes(graph.nodes).on("tick", ticked);
  simulation.force("link").links(graph.edges);
  // restart the simulation
  simulation.alpha(1).restart();

  function ticked() {
    link
      .attr("x1", function(d) {
        return d.source.x;
      })
      .attr("y1", function(d) {
        return d.source.y;
      })
      .attr("x2", function(d) {
        return d.target.x;
      })
      .attr("y2", function(d) {
        return d.target.y;
      });

    node.attr("transform", function(d) {
      return `translate(${d.x},${d.y})`;
    });
  }
}

// dragging functions
function dragstarted(d) {
  if (!d3.event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x;
  d.fy = d.y;
}

function dragged(d) {
  d.fx = d3.event.x;
  d.fy = d3.event.y;
}

// function dragended(d) {
//   if (!d3.event.active) simulation.alphaTarget(1);
//   d.fx = null;
//   d.fy = null;
// }

//Zoom functions
function zoom_actions() {
  g.attr("transform", d3.event.transform);
}

// responsivefy from https://brendansudol.com/writing/responsive-d3
function responsivefy(svg) {
  // get container + svg aspect ratio
  const container = d3.select(svg.node().parentNode),
    width = parseInt(svg.style("width")),
    height = parseInt(svg.style("height")),
    aspect = width / height;

  // add viewBox and preserveAspectRatio properties,
  // and call resize so that svg resizes on inital page load
  svg
    .attr("viewBox", "0 0 " + width + " " + height)
    .attr("preserveAspectRatio", "xMinYMid")
    .call(resize);

  // to register multiple listeners for same event type,
  // you need to add namespace, i.e., 'click.foo'
  // necessary if you call invoke this function for multiple svgs
  // api docs: https://github.com/mbostock/d3/wiki/Selections#on
  d3.select(window).on("resize." + container.attr("id"), resize);

  // get width of container and resize svg to fit it
  function resize() {
    const targetWidth = Math.floor(parseInt(container.style("width")) * 0.75);
    svg.attr("width", targetWidth);
    svg.attr("height", Math.round(targetWidth / aspect));
  }
}
