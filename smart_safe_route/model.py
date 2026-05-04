"""
model.py — K-Means + Logistic Regression (pure Python, no sklearn)
Works on real Indian location dataset.
"""
import math, random
random.seed(7)

from india_data import get_all_locations
from utils import compute_ess


# ── K-Means ──────────────────────────────────────────────────────────────────
class KMeans:
    def __init__(self, k=6, max_iters=150):
        self.k = k
        self.max_iters = max_iters
        self.centroids = []
        self.labels_ = []

    def fit(self, points):
        self.centroids = random.sample(points, self.k)
        for _ in range(self.max_iters):
            clusters = [[] for _ in range(self.k)]
            self.labels_ = []
            for p in points:
                dists = [self._dist(p, c) for c in self.centroids]
                best = dists.index(min(dists))
                clusters[best].append(p)
                self.labels_.append(best)
            new_c = []
            for ci, cl in enumerate(clusters):
                if cl:
                    new_c.append(tuple(sum(x[d] for x in cl) / len(cl) for d in range(len(cl[0]))))
                else:
                    new_c.append(random.choice(points))
            if new_c == self.centroids:
                break
            self.centroids = new_c
        return self

    def _dist(self, a, b):
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


# ── Logistic Regression ───────────────────────────────────────────────────────
class LogReg:
    def __init__(self, lr=0.08, epochs=800):
        self.lr = lr
        self.epochs = epochs
        self.w = [0.0] * 4
        self.b = 0.0

    def _sig(self, z):
        return 1 / (1 + math.exp(-max(-500, min(500, z))))

    def _fwd(self, x):
        return self._sig(self.b + sum(wi * xi for wi, xi in zip(self.w, x)))

    def fit(self, X, y):
        n = len(X)
        for _ in range(self.epochs):
            dw = [0.0] * 4
            db = 0.0
            for xi, yi in zip(X, y):
                e = self._fwd(xi) - yi
                for i in range(4):
                    dw[i] += e * xi[i]
                db += e
            self.w = [self.w[i] - self.lr * dw[i] / n for i in range(4)]
            self.b -= self.lr * db / n

    def predict(self, x):
        return "safe" if self._fwd(x) >= 0.5 else "unsafe"

    def proba(self, x):
        return round(self._fwd(x), 4)


# ── SafetyModel ───────────────────────────────────────────────────────────────
class SafetyModel:
    def __init__(self):
        self.km = KMeans(k=6)
        self.lr = LogReg()
        self._locs = None

    def train(self):
        locs = get_all_locations()
        self._locs = locs
        # K-Means on (lat, lng, crime_rate)
        pts = [(l["lat"], l["lng"], l["crime_rate"]) for l in locs]
        self.km.fit(pts)
        # Logistic Regression
        X = [[l["crime_rate"], l["lighting"], l["crowd_density"], l["sentiment"]] for l in locs]
        y = [l["safety_label"] for l in locs]
        self.lr.fit(X, y)
        acc = sum(1 for xi, yi in zip(X, y) if (self.lr._fwd(xi) >= 0.5) == bool(yi)) / len(y)
        print(f"  LogReg training accuracy: {acc:.1%}")

    def predict(self, crime_rate, lighting, crowd_density, sentiment):
        return self.lr.predict([crime_rate, lighting, crowd_density, sentiment])

    def hotspots(self):
        locs = self._locs or get_all_locations()
        pts = [(l["lat"], l["lng"], l["crime_rate"]) for l in locs]
        result = []
        for i, c in enumerate(self.km.centroids):
            cluster_pts = [p for j, p in enumerate(pts) if self.km.labels_[j] == i]
            avg_crime = c[2]
            label = "high" if avg_crime > 0.65 else ("medium" if avg_crime > 0.4 else "low")
            result.append({
                "lat": round(c[0], 5), "lng": round(c[1], 5),
                "crime_rate": round(avg_crime, 3),
                "intensity": round(min(1.0, avg_crime), 3),
                "label": label,
                "cluster_id": i,
                "count": len(cluster_pts),
            })
        result.sort(key=lambda x: x["crime_rate"], reverse=True)
        return result
