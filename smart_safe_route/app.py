"""
app.py — Flask backend for Smart Safe Route System (India)
"""
from flask import Flask, render_template, request, jsonify
from model import SafetyModel
from utils import compute_ess, find_route, haversine_km
from india_data import get_all_locations, get_cities, search_locations

app = Flask(__name__)

print("Initialising SafeRoute India...")
model = SafetyModel()
model.train()
print("Ready.")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/search")
def api_search():
    """Autocomplete: return matching locations for query string."""
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    matches = search_locations(q)[:8]
    return jsonify([
        {"label": f"{m['name']}, {m['city']}", "name": m["name"],
         "city": m["city"], "state": m["state"],
         "lat": m["lat"], "lng": m["lng"]}
        for m in matches
    ])


@app.route("/api/cities")
def api_cities():
    return jsonify(get_cities())


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    source  = data.get("source", "Connaught Place")
    dest    = data.get("destination", "Saket")
    time_of_day = data.get("time", "day")

    route, all_locs, graph, src_idx, dst_idx, light = \
        find_route(source, dest, time_of_day)

    # Add ML prediction to each waypoint
    enriched = []
    for wp in route:
        pred = model.predict(wp["crime_rate"], wp["lighting"],
                             wp["crowd_density"], wp["sentiment"])
        enriched.append({**wp, "prediction": pred})

    avg_ess = sum(w["ess"] for w in enriched) / max(len(enriched), 1)
    overall = "safe" if avg_ess >= 0.5 else "unsafe"

    # ── alternative routes (slightly randomised weights) ──────────
    import heapq, math, random
    def alt_dijkstra(noise=0.3):
        dist_map = {n: math.inf for n in graph}
        dist_map[src_idx] = 0.0
        prev = {n: None for n in graph}
        pq = [(0.0, src_idx)]
        vis = set()
        while pq:
            cost, u = heapq.heappop(pq)
            if u in vis: continue
            vis.add(u)
            if u == dst_idx: break
            for v, w, _ in graph.get(u, []):
                nc = cost + w * random.uniform(1 - noise, 1 + noise)
                if nc < dist_map[v]:
                    dist_map[v] = nc
                    prev[v] = u
                    heapq.heappush(pq, (nc, v))
        path, cur = [], dst_idx
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path if path[0] == src_idx else [src_idx, dst_idx]

    alt_routes = []
    seen_paths = {tuple(w["name"] for w in enriched)}
    random.seed(42)
    for _ in range(6):
        ap = alt_dijkstra(noise=0.4)
        ap_wps = []
        for idx in ap:
            l = all_locs[idx]
            ess = compute_ess(l["crime_rate"], light, l["crowd_density"], l["sentiment"])
            ap_wps.append({"name": l["name"], "city": l["city"],
                           "lat": l["lat"], "lng": l["lng"], "ess": ess})
        key = tuple(w["name"] for w in ap_wps)
        if key not in seen_paths:
            seen_paths.add(key)
            avg = sum(w["ess"] for w in ap_wps) / max(len(ap_wps), 1)
            alt_routes.append({"path": ap_wps, "avg_ess": round(avg, 3)})
        if len(alt_routes) >= 2:
            break

    # breakdown averages
    avg_crime  = sum(w["crime_rate"] for w in enriched) / len(enriched)
    avg_crowd  = sum(w["crowd_density"] for w in enriched) / len(enriched)
    avg_sent   = sum(w["sentiment"] for w in enriched) / len(enriched)

    return jsonify({
        "source": source, "destination": dest, "time": time_of_day,
        "route": enriched,
        "avg_ess": round(avg_ess, 3),
        "overall_prediction": overall,
        "breakdown": {
            "crime_safety": round(1 - avg_crime, 3),
            "lighting": light,
            "crowd_density": round(avg_crowd, 3),
            "sentiment": round(avg_sent, 3),
        },
        "alternative_routes": alt_routes,
        "total_waypoints": len(enriched),
    })


@app.route("/api/heatmap")
def api_heatmap():
    return jsonify({"hotspots": model.hotspots(), "total": len(model.hotspots())})


@app.route("/api/all_locations")
def api_all_locations():
    locs = get_all_locations()
    return jsonify([{
        "name": l["name"], "city": l["city"], "state": l["state"],
        "lat": l["lat"], "lng": l["lng"],
        "ess": l["ess"], "crime_rate": l["crime_rate"],
        "safety_label": l["safety_label"]
    } for l in locs])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
