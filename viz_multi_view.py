#!/usr/bin/env python3
"""
viz_multi_view.py

Generate a combined knowledge-graph + timeline + messages HTML visualization
from a proof_of_work JSON provenance.

Usage:
  python viz_multi_view.py proof.json [-o output.html] [--title TITLE]
"""
import os
import json
import argparse
from build_knowledge_graph import build_graph
from build_timeline_data import build_timeline_data
try:
    from pyvis.network import Network
except ImportError:
    raise ImportError("pyvis is required to run this script: pip install pyvis")

def main():
    parser = argparse.ArgumentParser(
        description='Visualize provenance with graph, timeline, and messages panes'
    )
    parser.add_argument('input_json', help='Path to proof_of_work JSON file')
    parser.add_argument('-o', '--output', help='Output HTML file', default=None)
    parser.add_argument('--title', help='Title for the visualization', default=None)
    args = parser.parse_args()

    # Load provenance JSON
    with open(args.input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    provenance = data.get('provenance', {})

    # Build networkx graph and export to vis DataSets
    G = build_graph(provenance)
    net = Network(height='100%', width='100%', directed=True, notebook=False)
    if args.title:
        net.heading = args.title
    net.from_nx(G)
    # Export nodes & edges as lists of dicts
    net_nodes = net.nodes
    net_edges = net.edges

    # Build timeline data (groups and items)
    groups, items = build_timeline_data(provenance)

    # Remove step subgroup rows under root agent but keep action/tool items
    root_agent = provenance.get('root_agent', {}) or {}
    root_name = root_agent.get('name')
    if root_name:
        # Filter out subgroup definitions for root agent steps
        filtered_groups = []
        for g in groups:
            gid = g.get('id')
            if gid == root_name:
                # clear nestedGroups for root agent
                if 'nestedGroups' in g:
                    g['nestedGroups'] = []
                filtered_groups.append(g)
            elif not (isinstance(gid, str) and gid.startswith(f"{root_name}-step-")):
                filtered_groups.append(g)
        groups = filtered_groups
        # Flatten items: move step and tool_call items to root swimlane
        for it in items:
            if it.get('group') == root_name and \
               isinstance(it.get('subgroup'), str) and \
               it['subgroup'].startswith(f"{root_name}-step-"):
                # remove subgroup so item appears on root group
                del it['subgroup']

    # Serialize JSON blobs for embedding
    net_nodes_json = json.dumps(net_nodes, indent=2)
    net_edges_json = json.dumps(net_edges, indent=2)
    groups_json = json.dumps(groups, indent=2)
    items_json = json.dumps(items, indent=2)

    title = args.title or os.path.basename(args.input_json)
    base = os.path.splitext(args.input_json)[0]
    out_file = args.output or f"{base}_multi.html"

    # Generate HTML with three-pane grid: graph | timeline | messages
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | Agent Insights</title>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <link href="https://unpkg.com/vis-timeline/styles/vis-timeline-graph2d.min.css" rel="stylesheet" />
  <script src="https://unpkg.com/vis-timeline/standalone/umd/vis-timeline-graph2d.min.js"></script>
  <style>
    :root {{
      --primary: #4361ee;
      --primary-light: #4895ef;
      --secondary: #3f37c9;
      --accent: #f72585;
      --success: #4cc9f0;
      --warning: #f8961e;
      --danger: #f94144;
      --light: #f8f9fa;
      --dark: #212529;
      --gray-100: #f8f9fa;
      --gray-200: #e9ecef;
      --gray-300: #dee2e6;
      --gray-400: #ced4da;
      --gray-500: #adb5bd;
      --gray-600: #6c757d;
      --gray-700: #495057;
      --gray-800: #343a40;
      --gray-900: #212529;
      
      /* Node type colors */
      --color-agent: #4361ee;
      --color-tool: #4cc9f0;
      --color-tool-call: #f72585;
      --color-observation: #3f37c9;
      --color-action: #4895ef;
      --color-step: #adb5bd;
      --color-final-answer: #7209b7;
    }}
    
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    
    body {{
      margin: 0;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      color: var(--gray-800);
      background-color: var(--gray-100);
      display: grid;
      grid-template-rows: auto 1fr auto;
      min-height: 100vh;
    }}
    
    /* Header */
    header {{
      background: linear-gradient(90deg, var(--primary) 0%, var(--secondary) 100%);
      color: white;
      padding: 1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
      z-index: 100;
    }}
    
    .logo {{
      display: flex;
      align-items: center;
      font-weight: 700;
      font-size: 1.5rem;
      color: white;
      text-decoration: none;
    }}
    
    .logo i {{
      margin-right: 0.5rem;
      font-size: 1.8rem;
    }}
    
    .header-actions {{
      display: flex;
      gap: 1rem;
    }}
    
    /* Main content */
    .container {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      grid-template-rows: auto 1fr;
      grid-template-areas:
        "controls controls"
        "main sidebar";
      height: calc(100vh - 130px);
      gap: 1rem;
      padding: 1rem;
    }}
    
    /* Controls */
    #controls {{
      grid-area: controls;
      background-color: white;
      padding: 1rem;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 1.5rem;
    }}
    
    .view-selector {{
      display: flex;
      align-items: center;
      background-color: var(--gray-200);
      border-radius: 6px;
      overflow: hidden;
    }}
    
    .view-selector label {{
      padding: 0.5rem 1rem;
      cursor: pointer;
      transition: all 0.2s ease;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    
    .view-selector input[type="radio"] {{
      display: none;
    }}
    
    .view-selector input[type="radio"]:checked + span {{
      background-color: var(--primary);
      color: white;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }}
    
    .view-selector span {{
      padding: 0.5rem 1rem;
      border-radius: 4px;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    
    .control-group {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    
    .control-group .label {{
      font-weight: 500;
      color: var(--gray-700);
    }}
    
    /* Main visualization area */
    .main-panel {{
      grid-area: main;
      background-color: white;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
      overflow: hidden;
      position: relative;
    }}
    
    #network, #timeline {{
      width: 100%;
      height: 100%;
    }}
    
    #timeline {{
      display: none;
    }}
    
    /* Sidebar */
    .sidebar {{
      grid-area: sidebar;
      background-color: white;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    
    .sidebar-header {{
      padding: 1rem;
      background-color: var(--gray-200);
      font-weight: 600;
      border-bottom: 1px solid var(--gray-300);
    }}
    
    #messages {{
      flex: 1;
      overflow-y: auto;
      padding: 1rem;
    }}
    
    .msg-box {{
      padding: 1rem;
      margin-bottom: 0.75rem;
      border-radius: 6px;
      background-color: var(--gray-100);
      cursor: pointer;
      transition: all 0.2s ease;
      border-left: 3px solid transparent;
    }}
    
    .msg-box:hover {{
      background-color: var(--gray-200);
    }}
    
    .msg-box.active {{
      background-color: rgba(67, 97, 238, 0.1);
      border-left-color: var(--primary);
    }}
    
    .msg-box-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.5rem;
    }}
    
    .msg-box-title {{
      font-weight: 600;
      color: var(--gray-800);
    }}
    
    .msg-box-type {{
      font-size: 0.75rem;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      background-color: var(--gray-200);
      color: var(--gray-700);
    }}
    
    .msg-box-type.agent {{ background-color: rgba(67, 97, 238, 0.2); color: var(--color-agent); }}
    .msg-box-type.tool {{ background-color: rgba(76, 201, 240, 0.2); color: var(--color-tool); }}
    .msg-box-type.tool_call {{ background-color: rgba(247, 37, 133, 0.2); color: var(--color-tool-call); }}
    .msg-box-type.observation {{ background-color: rgba(63, 55, 201, 0.2); color: var(--color-observation); }}
    .msg-box-type.action {{ background-color: rgba(72, 149, 239, 0.2); color: var(--color-action); }}
    .msg-box-type.step {{ background-color: rgba(173, 181, 189, 0.2); color: var(--color-step); }}
    .msg-box-type.final_answer {{ background-color: rgba(114, 9, 183, 0.2); color: var(--color-final-answer); }}
    
    /* hide message details by default, show when active */
    .msg-box pre {{
      display: none;
      background-color: var(--gray-100);
      padding: 0.75rem;
      margin-top: 0.75rem;
      border-radius: 4px;
      font-size: 0.85rem;
      border: 1px solid var(--gray-300);
      max-height: 300px;
      overflow-y: auto;
    }}
    
    .msg-box.active pre {{
      display: block;
    }}
    
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-wrap: break-word;
    }}
    
    /* Footer */
    footer {{
      background-color: var(--gray-800);
      color: var(--gray-300);
      padding: 1rem 2rem;
      text-align: center;
      font-size: 0.875rem;
    }}
    
    /* Responsive adjustments */
    @media (max-width: 1024px) {{
      .container {{
        grid-template-columns: 1fr;
        grid-template-areas:
          "controls"
          "main"
          "sidebar";
      }}
      
      .sidebar {{
        max-height: 300px;
      }}
    }}
    
    /* Tooltips */
    .tooltip {{
      position: relative;
      display: inline-block;
      cursor: help;
    }}
    
    .tooltip .tooltip-text {{
      visibility: hidden;
      width: 200px;
      background-color: var(--gray-800);
      color: white;
      text-align: center;
      border-radius: 6px;
      padding: 0.5rem;
      position: absolute;
      z-index: 1;
      bottom: 125%;
      left: 50%;
      transform: translateX(-50%);
      opacity: 0;
      transition: opacity 0.3s;
      font-size: 0.75rem;
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
    }}
    
    .tooltip:hover .tooltip-text {{
      visibility: visible;
      opacity: 1;
    }}
    
    /* Loading indicator */
    .loading {{
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: rgba(255, 255, 255, 0.8);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 1000;
    }}
    
    .loading-spinner {{
      width: 50px;
      height: 50px;
      border: 5px solid var(--gray-300);
      border-top: 5px solid var(--primary);
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }}
    
    @keyframes spin {{
      0% {{ transform: rotate(0deg); }}
      100% {{ transform: rotate(360deg); }}
    }}
  </style>
</head>
<body>
  <!-- Header -->
  <header>
    <a href="#" class="logo">
      <i class="fas fa-brain"></i>
      <span>Agent Insights</span>
    </a>
    <div class="header-actions">
      <div class="tooltip">
        <i class="fas fa-info-circle"></i>
        <span class="tooltip-text">Visualize agent execution with knowledge graphs and timelines</span>
      </div>
    </div>
  </header>

  <!-- Main content -->
  <div class="container">
    <div id="controls">
      <div class="view-selector">
        <label>
          <input type="radio" name="view" value="graph" checked>
          <span><i class="fas fa-project-diagram"></i> Knowledge Graph</span>
        </label>
        <label>
          <input type="radio" name="view" value="timeline">
          <span><i class="fas fa-stream"></i> Timeline</span>
        </label>
      </div>
      
      <div class="control-group">
        <span class="label">Run ID:</span>
        <strong>{data.get('run_id', 'Unknown')}</strong>
      </div>
      
      <div class="tooltip">
        <i class="fas fa-question-circle"></i>
        <span class="tooltip-text">Switch between graph and timeline views to explore agent execution from different perspectives</span>
      </div>
    </div>
    
    <div class="main-panel">
      <div id="network"></div>
      <div id="timeline"></div>
      <div class="loading" id="loading">
        <div class="loading-spinner"></div>
      </div>
    </div>
    
    <div class="sidebar">
      <div class="sidebar-header">
        <i class="fas fa-list-ul"></i> Execution Steps
      </div>
      <div id="messages"></div>
    </div>
  </div>
  
  <!-- Footer -->
  <footer>
    <p>© 2025 Agent Insights | Powered by SmolagentsAI</p>
  </footer>
  
  <script>
  // view toggle logic using radio buttons
  var netDiv = document.getElementById('network');
  var timDiv = document.getElementById('timeline');
  document.getElementsByName('view').forEach(function(radio) {{
    radio.onchange = function() {{
      if (this.value === 'graph') {{
        netDiv.style.display = 'block';
        timDiv.style.display = 'none';
        // redraw network when shown
        if (typeof network !== 'undefined' && network.redraw) {{ network.redraw(); }}
      }} else {{
        netDiv.style.display = 'none';
        timDiv.style.display = 'block';
        // optional: redraw timeline
        if (typeof timeline !== 'undefined' && timeline.redraw) {{ timeline.redraw(); }}
      }}
    }};
  }});
  
  // -- Knowledge Graph --
  var graphData = {{
    nodes: new vis.DataSet({net_nodes_json}),
    edges: new vis.DataSet({net_edges_json})
  }};
  
  // apply color coding by node type (background colors)
  var typeColors = {{
    'agent': 'var(--color-agent)',
    'tool': 'var(--color-tool)',
    'tool_call': 'var(--color-tool-call)',
    'observation': 'var(--color-observation)',
    'action': 'var(--color-action)',
    'step': 'var(--color-step)',
    'final_answer': 'var(--color-final-answer)'
  }};
  
  // update node colors in the DataSet
  graphData.nodes.get().forEach(function(node) {{
    var c = typeColors[node.type];
    if (c) {{
      graphData.nodes.update({{ 
        id: node.id, 
        color: {{ 
          background: c,
          border: c,
          highlight: {{
            background: c,
            border: '#000000'
          }}
        }},
        font: {{
          color: '#ffffff'
        }}
      }});
    }}
  }});
  
  var networkOptions = {{
    interaction: {{ 
      hover: true,
      navigationButtons: true,
      keyboard: true
    }},
    edges: {{ 
      arrows: {{ to: true }},
      smooth: {{
        enabled: true,
        type: 'dynamic',
        roundness: 0.5
      }}
    }},
    physics: {{
      stabilization: {{
        iterations: 100,
        fit: true
      }},
      barnesHut: {{
        gravitationalConstant: -2000,
        centralGravity: 0.1,
        springLength: 150,
        springConstant: 0.05,
        damping: 0.09
      }}
    }},
    layout: {{
      improvedLayout: true,
      hierarchical: {{
        enabled: false
      }}
    }}
  }};
  
  var network = new vis.Network(
    document.getElementById('network'),
    graphData,
    networkOptions
  );
  
  // ensure network knows its container size
  network.setSize('100%', '100%');
  network.on('stabilizationIterationsDone', function() {{
    document.getElementById('loading').style.display = 'none';
  }});
  
  // redraw on window resize
  window.addEventListener('resize', function() {{ network.redraw(); }});
  // ensure initial redraw after page load
  window.addEventListener('load', function() {{ if (network && network.redraw) network.redraw(); }});

  // -- Timeline View --
  var timelineGroups = new vis.DataSet({groups_json});
  var timelineItems = new vis.DataSet({items_json});
  var timelineOptions = {{
    selectable: true,
    showCurrentTime: false,
    showNested: true,
    stack: true,
    zoomKey: 'ctrlKey',
    zoomMax: 31536000000, // 1 year in ms
    zoomMin: 1000, // 1 second in ms
    orientation: 'top',
    tooltip: {{
      followMouse: true,
      overflowMethod: 'cap'
    }}
  }};
  
  var timeline = new vis.Timeline(
    document.getElementById('timeline'),
    timelineItems,
    timelineGroups,
    timelineOptions
  );

  // -- Messages Pane --
  var allNodes = new vis.DataSet({net_nodes_json});
  var messagesDiv = document.getElementById('messages');
  
  // Create one clickable box per graph node
  allNodes.forEach(node => {{
    var b = document.createElement('div');
    b.className = 'msg-box';
    b.dataset.nodeId = node.id;
    
    // Create header with title and type badge
    var header = document.createElement('div');
    header.className = 'msg-box-header';
    
    var title = document.createElement('div');
    title.className = 'msg-box-title';
    title.textContent = node.label || node.id;
    header.appendChild(title);
    
    if (node.type) {{
      var typeBadge = document.createElement('div');
      typeBadge.className = 'msg-box-type ' + node.type;
      typeBadge.textContent = node.type;
      header.appendChild(typeBadge);
    }}
    
    b.appendChild(header);
    
    // Add sequence number if available
    if (node.sequence !== undefined) {{
      var seq = document.createElement('div');
      seq.style.fontSize = '0.8rem';
      seq.style.color = 'var(--gray-600)';
      seq.textContent = 'Sequence: ' + node.sequence;
      b.appendChild(seq);
    }}
    
    // attach hidden message details (JSON content)
    var pre = document.createElement('pre');
    pre.textContent = JSON.stringify(node, null, 2);
    b.appendChild(pre);
    
    b.onclick = () => {{
      // highlight message box and show details
      document.querySelectorAll('.msg-box.active').forEach(e => e.classList.remove('active'));
      b.classList.add('active');
      b.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
      // select node in graph
      network.selectNodes([node.id]);
      network.focus(node.id, {{ scale: 1.2 }});
    }};
    
    messagesDiv.appendChild(b);
  }});
  
  // Highlight message when a node is selected in the graph
  network.on('selectNode', (params) => {{
    var sel = params.nodes[0];
    var el = document.querySelector('.msg-box[data-node-id="' + sel + '"]');
    if (el) {{
      document.querySelectorAll('.msg-box.active').forEach(e => e.classList.remove('active'));
      el.classList.add('active');
      el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}
  }});
  
  // Timeline selection event
  timeline.on('select', function(properties) {{
    if (properties.items && properties.items.length > 0) {{
      var itemId = properties.items[0];
      var item = timelineItems.get(itemId);
      
      // Find corresponding node in the graph if possible
      var matchingNodeId = null;
      allNodes.forEach(function(node) {{
        if (node.id.includes(itemId) || (node.sequence !== undefined && item.content.includes(node.sequence))) {{
          matchingNodeId = node.id;
        }}
      }});
      
      if (matchingNodeId) {{
        var el = document.querySelector('.msg-box[data-node-id="' + matchingNodeId + '"]');
        if (el) {{
          document.querySelectorAll('.msg-box.active').forEach(e => e.classList.remove('active'));
          el.classList.add('active');
          el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        }}
      }}
    }}
  }});
  </script>
</body>
</html>"""

    # Write out the combined HTML
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Multi-view visualization written to {out_file}")

if __name__ == '__main__':
    main()