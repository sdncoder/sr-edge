import sys
import networkx as nx
import matplotlib.pyplot as plt
import csv

EDGES_FILE = "edges.csv"
NODES_FILE = "nodes.csv"

G = nx.Graph()
with open(EDGES_FILE) as f:
    for row in csv.reader(f):
        if len(row) >= 3:
            src, dst, weight = row[0].strip(), row[1].strip(), float(row[2].strip())
            capacity = float(row[3].strip()) if len(row) >= 4 else 100.0
            G.add_edge(src, dst, weight=weight, capacity=capacity)

pos = {}
with open(NODES_FILE) as f:
    reader = csv.DictReader(f)
    for row in reader:
        pos[row["node"].strip()] = (float(row["x"]), float(row["y"]))
pos = pos or nx.spring_layout(G, seed=42)
nodes = sorted(G.nodes())

failed_edges = set()
demands = []  # list of {source, target, gbps, path, cost}
edge_lines = {}


def pick_node(prompt):
    while True:
        val = input(prompt).strip()
        if val in nodes:
            return val
        if val.isdigit() and 1 <= int(val) <= len(nodes):
            return nodes[int(val) - 1]
        print(f"  Invalid — enter a node name or number (1-{len(nodes)})")


def pick_gbps():
    while True:
        val = input("  Demand (Gbps): ").strip()
        try:
            d = float(val)
            if d > 0:
                return d
        except ValueError:
            pass
        print("  Invalid — enter a positive number")


def compute_flow():
    """Aggregate flow across all active demands."""
    flow = {tuple(sorted([u, v])): 0.0 for u, v in G.edges()}
    for d in demands:
        for i in range(len(d["path"]) - 1):
            key = tuple(sorted([d["path"][i], d["path"][i + 1]]))
            flow[key] += d["gbps"]
    return flow


def get_path(source, target, gbps):
    """Capacity-constrained Dijkstra: skips edges where remaining capacity < gbps."""
    flow = compute_flow()
    H = G.copy()
    for u, v in failed_edges:
        if H.has_edge(u, v):
            H.remove_edge(u, v)
    for u, v in list(H.edges()):
        key = tuple(sorted([u, v]))
        if H[u][v]["capacity"] - flow.get(key, 0.0) < gbps:
            H.remove_edge(u, v)
    try:
        path = nx.dijkstra_path(H, source, target, weight="weight")
        cost = nx.dijkstra_path_length(H, source, target, weight="weight")
        return path, cost
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return [], None


def reroute_all():
    """Re-route all demands from scratch after a topology change."""
    for d in demands:
        d["path"] = []
        d["cost"] = None
    for d in demands:
        path, cost = get_path(d["source"], d["target"], d["gbps"])
        d["path"] = path
        d["cost"] = cost


def util_color(ratio):
    if ratio < 0.5:
        return "green"
    elif ratio < 0.8:
        return "orange"
    return "red"


def draw(ax):
    global edge_lines
    ax.clear()
    edge_lines = {}

    flow = compute_flow()

    for u, v in G.edges():
        edge_key = tuple(sorted([u, v]))
        x = [pos[u][0], pos[v][0]]
        y = [pos[u][1], pos[v][1]]

        if edge_key in failed_edges:
            color, lw, ls = "red", 2, "--"
        else:
            cap = G[u][v]["capacity"]
            f = flow.get(edge_key, 0.0)
            ratio = f / cap if cap > 0 else 0.0
            color = util_color(ratio) if f > 0 else "lightgray"
            lw = 2 + ratio * 3
            ls = "-"

        line, = ax.plot(x, y, color=color, linewidth=lw, linestyle=ls, picker=5, zorder=1)
        edge_lines[line] = edge_key

    nx.draw_networkx_nodes(G, pos, ax=ax, node_color="white", node_size=700, edgecolors="black", linewidths=1.5)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=10, font_weight="bold")

    edge_labels = {}
    for u, v, data in G.edges(data=True):
        edge_key = tuple(sorted([u, v]))
        f = flow.get(edge_key, 0.0)
        cap = data["capacity"]
        if f > 0:
            edge_labels[(u, v)] = f"{f:.0f}/{cap:.0f} ({f/cap*100:.0f}%)"
        else:
            edge_labels[(u, v)] = data["weight"]
    nx.draw_networkx_edge_labels(G, pos, ax=ax, edge_labels=edge_labels, font_size=8)

    active = sum(1 for d in demands if d["path"])
    blocked = len(demands) - active
    status = f"{active} demand(s) active"
    if blocked:
        status += f"  |  {blocked} unroutable"
    ax.set_title(f"{status}  |  click edge to fail/restore")
    ax.axis("off")


# --- Demand collection ---
print("Available nodes:")
for i, n in enumerate(nodes):
    print(f"  {i + 1}. {n}")

while True:
    print(f"\nDemand {len(demands) + 1}  (press Enter with no source to finish):")
    val = input("  Source node: ").strip()
    if not val:
        if not demands:
            print("  Enter at least one demand.")
            continue
        break
    if val in nodes:
        source = val
    elif val.isdigit() and 1 <= int(val) <= len(nodes):
        source = nodes[int(val) - 1]
    else:
        print("  Invalid node.")
        continue
    target = pick_node("  Target node: ")
    gbps = pick_gbps()
    path, cost = get_path(source, target, gbps)
    demands.append({"source": source, "target": target, "gbps": gbps, "path": path, "cost": cost})
    if path:
        print(f"  -> {' -> '.join(path)}  (cost: {cost})")
    else:
        print(f"  -> No feasible path — insufficient capacity or no route")

# --- Plot ---
fig, ax = plt.subplots(figsize=(10, 7))
draw(ax)


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

    reroute_all()
    for d in demands:
        if d["path"]:
            print(f"  {d['source']}->{d['target']} {d['gbps']:.0f}G: {' -> '.join(d['path'])}  (cost: {d['cost']})")
        else:
            print(f"  {d['source']}->{d['target']} {d['gbps']:.0f}G: NO PATH")
    draw(ax)
    fig.canvas.draw()


fig.canvas.mpl_connect("pick_event", on_pick)
plt.tight_layout()
plt.show()
