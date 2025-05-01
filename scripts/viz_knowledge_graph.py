#!/usr/bin/env python3
"""
viz_knowledge_graph.py

Generate an interactive HTML visualization of a proof_of_work JSON knowledge graph.
This script reads the provenance JSON, builds a NetworkX graph, and uses PyVis to emit
an HTML file you can open in your browser.

Usage:
  pip install networkx pyvis
  python viz_knowledge_graph.py proof_of_work_20250428_145452.json
"""
import os
import json
import argparse


import networkx as nx
try:
    from pyvis.network import Network
except ImportError:
    raise ImportError("pyvis is required to run this script: pip install pyvis")

from build_knowledge_graph import build_graph


def main():
    parser = argparse.ArgumentParser(
        description="Visualize a proof_of_work JSON as an interactive HTML graph"
    )
    parser.add_argument(
        'input_json', help='Path to proof_of_work JSON file'
    )
    parser.add_argument(
        '-o', '--output', help='Output HTML file', default=None
    )
    parser.add_argument(
        '--title', help='Title for the visualization', default=None
    )
    args = parser.parse_args()

    # Load proof_of_work JSON
    with open(args.input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    provenance = data.get('provenance', {})

    # Build NetworkX graph
    G = build_graph(provenance)

    # Initialize PyVis network
    net = Network(
        height='750px', width='100%', directed=True, notebook=False
    )
    if args.title:
        net.heading = args.title
    # Transfer nodes & edges
    net.from_nx(G)
    # Define color mapping for node types to visually distinguish categories
    type_colors = {
        'agent': '#FF6666',
        'tool': '#66FF66',
        'tool_call': '#FF9966',
        'observation': '#6666FF',
        'action': '#FFCC66',
        'step': '#CCCCCC',
        'final_answer': '#CC66FF'
    }
    # Enrich nodes: set concise labels, color-code by type, and show full attributes on click/hover
    for node in net.nodes:
        node_id = node.get('id')
        # original node attributes from NetworkX graph
        attrs = G.nodes.get(node_id, {})
        # build label: for tool calls show the tool name, otherwise type; append sequence if present
        if attrs.get('type') == 'tool_call':
            label = attrs.get('tool', node_id)
        else:
            label = attrs.get('type', node_id)
        if 'sequence' in attrs:
            label = f"{label}:{attrs['sequence']}"
        node['label'] = label
        # build HTML tooltip showing all attributes
        try:
            info = json.dumps(attrs, indent=2, ensure_ascii=False)
        except Exception:
            info = str(attrs)
        node['title'] = f"<pre>{info}</pre>"
        # apply color if type matches
        node_type = attrs.get('type')
        color = type_colors.get(node_type)
        if color:
            node['color'] = color
    # Compute time sequence for each node (for timeline playback)
    seq_times = {}
    # agents at time 0
    for nid, nattrs in G.nodes(data=True):
        if nattrs.get('type') == 'agent':
            seq_times[nid] = 0
    # steps/actions/final_answer use their sequence field
    for nid, nattrs in G.nodes(data=True):
        seq = nattrs.get('sequence')
        if seq is not None:
            seq_times[nid] = seq
    # tools inherit time of first caller
    for nid, nattrs in G.nodes(data=True):
        if nattrs.get('type') == 'tool':
            caller_seqs = [G.nodes[p].get('sequence') for p in G.predecessors(nid)
                           if G.nodes[p].get('sequence') is not None]
            if caller_seqs:
                seq_times[nid] = min(caller_seqs)
    # tool_call nodes inherit time of their calling step
    for nid, nattrs in G.nodes(data=True):
        if nattrs.get('type') == 'tool_call':
            caller_seqs = [G.nodes[p].get('sequence') for p in G.predecessors(nid)
                           if G.nodes[p].get('sequence') is not None]
            if caller_seqs:
                seq_times[nid] = min(caller_seqs)
    # annotate nodes in net with sequence and find max
    max_seq = 0
    for node in net.nodes:
        nid = node.get('id')
        t = seq_times.get(nid, 0)
        node['sequence'] = t
        if t > max_seq:
            max_seq = t
    # Prepare interactive HTML with graph and message pane
    base = os.path.splitext(args.input_json)[0]
    out_file = args.output or f"{base}.html"
    # Prepare full list of nodes and a filtered network without observation leaves
    all_nodes = net.nodes
    # identify observation node IDs from original NetworkX graph
    obs_ids = [nid for nid, attrs in G.nodes(data=True) if attrs.get('type') == 'observation']
    # network visualization should omit observation-only nodes/edges
    net_nodes = [node for node in all_nodes if node.get('id') not in obs_ids]
    net_edges = [edge for edge in net.edges if edge.get('to') not in obs_ids and edge.get('from') not in obs_ids]
    all_nodes_json = json.dumps(all_nodes, indent=2, ensure_ascii=False)
    net_nodes_json = json.dumps(net_nodes, indent=2, ensure_ascii=False)
    net_edges_json = json.dumps(net_edges, indent=2, ensure_ascii=False)
    # Build HTML template with a split view: graph on left, messages on right
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{args.title or os.path.basename(out_file)}</title>
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; }}
    /* Timeline controls bar */
    #controls {{ position: fixed; top: 0; left: 0; right: 0; height: 50px; background: #fafafa; z-index: 2; padding: 8px; box-sizing: border-box; border-bottom: 1px solid #ddd; }}
    /* Graph and messages below controls */
    #network {{ position: absolute; top: 50px; left: 0; width: 70%; height: calc(100vh - 50px); float: left; border-right: 1px solid #ddd; }}
    #messages {{ position: absolute; top: 50px; right: 0; width: 28%; height: calc(100vh - 50px); overflow-y: auto; float: right; padding: 10px; box-sizing: border-box; }}
    .msg-box {{ padding: 8px; margin-bottom: 8px; border: 1px solid #ccc; border-radius: 4px; cursor: pointer; }}
    .msg-box.active {{ background-color: #eef; border-color: #66a; }}
    pre {{ margin: 0; white-space: pre-wrap; word-wrap: break-word; }}
  </style>
  </style>
</head>
<body>
  <div id="controls">
    <label>Time: <span id="timeLabel">{max_seq}</span></label>
    <input type="range" id="timeSlider" min="0" max="{max_seq}" value="{max_seq}" step="1" style="width:90%; vertical-align:middle;">
  </div>
  <div id="network"></div>
  <div id="messages"></div>
<script>
// all nodes for the message pane
var allNodes = new vis.DataSet({all_nodes_json});
// filtered nodes/edges for the network view (no standalone observations)
var networkNodes = new vis.DataSet({net_nodes_json});
var networkEdges = new vis.DataSet({net_edges_json});
var container = document.getElementById('network');
 var data = {{ nodes: networkNodes, edges: networkEdges }};
 // Default physics-based layout
 var options = {{
  physics: {{ stabilization: true }},
  interaction: {{ hover: true }},
  edges: {{ arrows: {{ to: true }} }}
}};
 var network = new vis.Network(container, data, options);
    // disable physics after initial stabilization to keep positions fixed
    network.once('stabilizationIterationsDone', function() {{
      network.setOptions({{ physics: false }});
    }});
    // Timeline support: filter graph by node.sequence (hiding nodes/edges)
    var fullNetworkNodes = networkNodes.get();
    var fullNetworkEdges = networkEdges.get();
    var slider = document.getElementById('timeSlider');
    var timeLabel = document.getElementById('timeLabel');
    function filterGraph(t) {{
      var tVal = +t;
      // update node visibility
      var updateNodes = fullNetworkNodes.map(function(n) {{
        var hidden = n.sequence > tVal;
        return {{ id: n.id, hidden: hidden }};
      }});
      networkNodes.update(updateNodes);
      // update edge visibility
      var updateEdges = fullNetworkEdges.map(function(e) {{
        var fromSeq = (fullNetworkNodes.find(function(n) {{ return n.id === e.from; }}) || {{sequence:0}}).sequence;
        var toSeq = (fullNetworkNodes.find(function(n) {{ return n.id === e.to; }}) || {{sequence:0}}).sequence;
        var hidden = fromSeq > tVal || toSeq > tVal;
        return {{ id: e.id, hidden: hidden }};
      }});
      networkEdges.update(updateEdges);
    }}
    slider.addEventListener('input', function() {{
      filterGraph(this.value);
      timeLabel.innerText = this.value;
    }});
    // initialize view at max
    filterGraph(slider.value);

// Populate messages pane (clickable list of all nodes)
var messagesDiv = document.getElementById('messages');
allNodes.forEach(function(node) {{
  var box = document.createElement('div');
  box.className = 'msg-box';
  box.dataset.nodeId = node.id;
  var inner = '<strong>' + node.label + '</strong>' + (node.title || '');
  box.innerHTML = inner;
  box.addEventListener('click', function() {{
    // select and focus this node (if present) in network
    network.selectNodes([node.id]);
    network.focus(node.id, {{ scale: 1.2 }});
    updateActiveBox(node.id);
  }});
  messagesDiv.appendChild(box);
}});

function updateActiveBox(activeId) {{
  var boxes = document.getElementsByClassName('msg-box');
  for (var i = 0; i < boxes.length; i++) {{
    var b = boxes[i];
    if (b.dataset.nodeId == activeId) {{
      b.classList.add('active');
      b.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }} else {{
      b.classList.remove('active');
    }}
  }}
}}

network.on('selectNode', function(params) {{
  if (params.nodes.length > 0) {{
    updateActiveBox(params.nodes[0]);
  }}
}});
network.on('deselectNode', function() {{
  var boxes = document.getElementsByClassName('msg-box');
  for (var i = 0; i < boxes.length; i++) boxes[i].classList.remove('active');
}});
</script>
</body>
</html>"""
    # Write out custom HTML
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Interactive visualization written to {out_file}")


if __name__ == '__main__':
    main()