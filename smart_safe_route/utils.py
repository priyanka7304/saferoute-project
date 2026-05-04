"""
utils.py — Route graph, Dijkstra, and safety scoring
Uses real Indian location data from india_data.py
"""

import math
import heapq
from india_data import get_all_locations, search_locations


def compute_ess(crime_rate, lighting, crowd_density, sentiment):
    """
    Emotional Safety Score (ESS):
      (1 - crime_rate) x 0.4  — crime inverted
      lighting         x 0.2
      crowd_density    x 0.2
      sentiment        x 0.2
    Returns float [0, 1]. Higher = safer.
    """
    ess = (1 - crime_rate) * 0.4 + lighting * 0.2 + crowd_density * 0.2 + sentiment * 0.2
    return round(max(0.0, min(1.0, ess)), 4)


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance in km."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_graph(locations, lighting_override=None):
    """
    Build weighted graph. Edge weight = dist_km x danger_factor.
    """
    n = len(locations)
    graph = {i: [] for i in range(n)}
    for i, src in enumerate(locations):
        for j, dst in enumerate(locations):
            if i == j:
                continue
            dist = haversine_km(src["lat"], src["lng"], dst["lat"], dst["lng"])
            if dist > 15:
                continue
            light = lighting_override if lighting_override is not None else dst["lighting"]
            ess = compute_ess(dst["crime_rate"], light, dst["crowd_density"], dst["sentiment"])
            danger = max(0.05, 1.0 - ess)
            weight = round(dist * danger, 6)
            graph[i].append((j, weight, dist))
    return graph


def dijkstra(graph, start, end):
    """Standard Dijkstra. Returns (path_indices, total_cost)."""
    dist_map = {n: math.inf for n in graph}
    dist_map[start] = 0.0
    prev = {n: None for n in graph}
    pq = [(0.0, start)]
    visited = set()
    while pq:
        cost, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)
        if u == end:
            break
        for v, w, _ in graph.get(u, []):
            nc = cost + w
            if nc < dist_map[v]:
                dist_map[v] = nc
                prev[v] = u
                heapq.heappush(pq, (nc, v))
    path, cur = [], end
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    if not path or path[0] != start:
        return [start, end], dist_map.get(end, 0)
    return path, dist_map[end]


def find_route(source_name, dest_name, time_of_day="day"):
    """Find safest route between two Indian locations."""
    locations = get_all_locations()
    lighting_override = 1 if time_of_day == "day" else 0

    src_matches = search_locations(source_name)
    dst_matches = search_locations(dest_name)
    if not src_matches:
        src_matches = locations[:1]
    if not dst_matches:
        dst_matches = [locations[-1]]

    src_loc = src_matches[0]
    dst_loc = dst_matches[0]

    src_idx = next((i for i, l in enumerate(locations) if l["name"] == src_loc["name"]), 0)
    dst_idx = next((i for i, l in enumerate(locations) if l["name"] == dst_loc["name"]), len(locations) - 1)

    graph = build_graph(locations, lighting_override)
    path_idx, _ = dijkstra(graph, src_idx, dst_idx)

    route = []
    for idx in path_idx:
        loc = locations[idx]
        light = lighting_override
        ess = compute_ess(loc["crime_rate"], light, loc["crowd_density"], loc["sentiment"])
        route.append({
            "name": loc["name"], "city": loc["city"], "state": loc["state"],
            "lat": loc["lat"], "lng": loc["lng"], "ess": ess,
            "crime_rate": round(loc["crime_rate"], 3),
            "lighting": light,
            "crowd_density": round(loc["crowd_density"], 3),
            "sentiment": round(loc["sentiment"], 3),
            "safety_label": loc["safety_label"],
        })
    return route, locations, graph, src_idx, dst_idx, lighting_override
