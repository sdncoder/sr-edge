import networkx as nx
import matplotlib.pyplot as plt
import csv

EDGES_FILE = "edges.csv"
NODES_FILE = "nodes.csv"

# Load graph from edges.csv
G = nx.Graph()
with open(EDGES_FILE) as f:
    for row in csv.reader(f):
        if len(row) == 3:
            src, dst, weight = row[0].strip(), row[1].strip(), float(row[2].strip())
            G.add_edge(src, dst, weight=weight)

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

def draw(ax, path, cost):
    global edge_lines
    ax.clear()
    edge_lines = {}

    path_edges = set()
    if path:
        for i in range(len(path) - 1):
            path_edges.add(tuple(sorted([path[i], path[i + 1]])))

    # Draw each edge individually so they are clickable
    for u, v in G.edges():
        edge_key = tuple(sorted([u, v]))
        x = [pos[u][0], pos[v][0]]
        y = [pos[u][1], pos[v][1]]

        if edge_key in failed_edges:
            color, lw, ls = "red", 2, "--"
        elif edge_key in path_edges:
            color, lw, ls = "green", 3, "-"
        else:
            color, lw, ls = "lightgray", 2, "-"

        line, = ax.plot(x, y, color=color, linewidth=lw, linestyle=ls, picker=5, zorder=1)
        edge_lines[line] = edge_key

    # Draw nodes
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color="white", node_size=700, edgecolors="black", linewidths=1.5)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=10, font_weight="bold")

    # Edge weight labels
    edge_labels = nx.get_edge_attributes(G, "weight")
    nx.draw_networkx_edge_labels(G, pos, ax=ax, edge_labels=edge_labels, font_size=8)

    if path:
        title = f"Path: {' -> '.join(path)}  (cost: {cost})  |  click edge to fail/restore"
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
    print(f"Path: {' -> '.join(path) if path else 'none'}  (cost: {cost})")
    draw(ax, path, cost)
    fig.canvas.draw()

fig.canvas.mpl_connect("pick_event", on_pick)
plt.tight_layout()
plt.show()
