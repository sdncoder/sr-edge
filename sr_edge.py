import networkx as nx
import matplotlib.pyplot as plt
import csv

EDGES_FILE = "edges.csv"
NODES_FILE = "nodes.csv"

# Load graph from edges.csv
G = nx.Graph()
with open(EDGES_FILE) as f:
    for row in csv.reader(f):
        if len(row) >= 3:
            src, dst, weight = row[0].strip(), row[1].strip(), float(row[2].strip())
            capacity = float(row[3].strip()) if len(row) >= 4 else 100.0
            G.add_edge(src, dst, weight=weight, capacity=capacity)

# Load fixed positions from nodes.csv
pos = {}
with open(NODES_FILE) as f:
    reader = csv.DictReader(f)
    for row in reader:
        pos[row["node"].strip()] = (float(row["x"]), float(row["y"]))

pos = pos or nx.spring_layout(G, seed=42)
nodes = sorted(G.nodes())

# Prompt user to select source and target
print("Available nodes:")
for i, n in enumerate(nodes):
    print(f"  {i + 1}. {n}")

def pick_node(prompt):
    while True:
        val = input(prompt).strip()
        if val in nodes:
            return val
        if val.isdigit() and 1 <= int(val) <= len(nodes):
            return nodes[int(val) - 1]
        print(f"  Invalid — enter a node name or number (1-{len(nodes)})")

source = pick_node("\nSelect A (source) node: ")
target = pick_node("Select Z (target) node: ")

def pick_demand():
    while True:
        val = input("Enter demand (Gbps): ").strip()
        try:
            d = float(val)
            if d > 0:
                return d
        except ValueError:
            pass
        print("  Invalid — enter a positive number")

demand = pick_demand()

failed_edges = set()
edge_lines = {}

def get_path():
    H = G.copy()
    for u, v in failed_edges:
        if H.has_edge(u, v):
            H.remove_edge(u, v)
    try:
        path = nx.dijkstra_path(H, source, target, weight="weight")
        cost = nx.dijkstra_path_length(H, source, target, weight="weight")
        return path, cost
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return [], None

def compute_flow(path):
    flow = {}
    for u, v in G.edges():
        flow[tuple(sorted([u, v]))] = 0.0
    for i in range(len(path) - 1):
        key = tuple(sorted([path[i], path[i + 1]]))
        flow[key] = demand
    return flow

def util_color(ratio):
    if ratio < 0.5:
        return "green"
    elif ratio < 0.8:
        return "orange"
    else:
        return "red"

def draw(ax, path, cost):
    global edge_lines
    ax.clear()
    edge_lines = {}

    path_edges = set()
    if path:
        for i in range(len(path) - 1):
            path_edges.add(tuple(sorted([path[i], path[i + 1]])))

    flow = compute_flow(path) if path else {}

    # Draw each edge individually so they are clickable
    for u, v in G.edges():
        edge_key = tuple(sorted([u, v]))
        x = [pos[u][0], pos[v][0]]
        y = [pos[u][1], pos[v][1]]

        if edge_key in failed_edges:
            color, lw, ls = "red", 2, "--"
        elif edge_key in path_edges:
            cap = G[u][v]["capacity"]
            ratio = demand / cap
            color = util_color(ratio)
            lw = 3 + ratio * 2
            ls = "-"
        else:
            color, lw, ls = "lightgray", 2, "-"

        line, = ax.plot(x, y, color=color, linewidth=lw, linestyle=ls, picker=5, zorder=1)
        edge_lines[line] = edge_key

    # Draw nodes
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color="white", node_size=700, edgecolors="black", linewidths=1.5)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=10, font_weight="bold")

    # Edge labels: flow/capacity on path edges, weight elsewhere
    edge_labels = {}
    for u, v, data in G.edges(data=True):
        edge_key = tuple(sorted([u, v]))
        if edge_key in path_edges:
            cap = data["capacity"]
            util = (demand / cap) * 100
            edge_labels[(u, v)] = f"{demand:.0f}/{cap:.0f} ({util:.0f}%)"
        else:
            edge_labels[(u, v)] = data["weight"]
    nx.draw_networkx_edge_labels(G, pos, ax=ax, edge_labels=edge_labels, font_size=8)

    if path:
        title = f"Path: {' -> '.join(path)}  (cost: {cost}, demand: {demand} Gbps)  |  click edge to fail/restore"
    else:
        title = "No path found  |  click edge to fail/restore"
    ax.set_title(title)
    ax.axis("off")

fig, ax = plt.subplots(figsize=(10, 7))
path, cost = get_path()
draw(ax, path, cost)

def on_pick(event):
    line = event.artist
    if line not in edge_lines:
        return
    edge_key = edge_lines[line]
    if edge_key in failed_edges:
        failed_edges.remove(edge_key)
        print(f"Restored: {edge_key[0]} -- {edge_key[1]}")
    else:
        failed_edges.add(edge_key)
        print(f"Failed:   {edge_key[0]} -- {edge_key[1]}")

    path, cost = get_path()
    if path:
        cap = G[path[0]][path[1]]["capacity"]
        util = (demand / cap) * 100
        print(f"Path: {' -> '.join(path)}  (cost: {cost}) | flow: {demand:.0f}/{cap:.0f} ({util:.0f}%) per hop")
    else:
        print("Path: none")
    draw(ax, path, cost)
    fig.canvas.draw()

fig.canvas.mpl_connect("pick_event", on_pick)
plt.tight_layout()
plt.show()
