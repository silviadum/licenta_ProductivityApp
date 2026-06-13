#!/usr/bin/env python3
"""
ml_engine.py — Productivity Intelligence Engine
================================================
Pipeline complet de Machine Learning pentru ProductivityApp:

  Modul 1. Predicția productivității (Regresie supervizată):
           - Ridge Regression (baseline liniar)
           - Gradient Boosting (model nonlinear cu performanță superioară)
           - Feature engineering: lag features, rolling mean, cyclical encoding
           - Evaluare: R², MAE, RMSE + cross-validation k-fold
           - Feature importance (din modelul nonlinear)

  Modul 2. Gruparea comportamentală (Clustering nesupervizat):
           - K-Means cu Elbow method + Silhouette score
           - PCA pentru vizualizare 2D
           - Profilarea clusterelor (zile de focus / întreținere / odihnă)

Rulare:
    python ml_engine.py --user 4 --train        # antrenează și salvează modelele
    python ml_engine.py --user 4 --predict      # prezice scorul de mâine
    python ml_engine.py --user 4 --report       # generează rapoarte PNG pentru lucrare
"""

import argparse
import json
import os
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, silhouette_score
from sklearn.model_selection import KFold, cross_val_score
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ─── Configurare ─────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8080/api"
MODELS_DIR = Path(__file__).parent / "models"
REPORTS_DIR = Path(__file__).parent / "reports"
MODELS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Temă vizuală
matplotlib.rcParams.update({
    "figure.facecolor": "#111111", "axes.facecolor": "#1a1a1a",
    "text.color": "#e0d5c8", "axes.labelcolor": "#e0d5c8",
    "xtick.color": "#888", "ytick.color": "#888",
    "axes.edgecolor": "#333", "grid.color": "#2a2a2a",
    "axes.spines.top": False, "axes.spines.right": False,
})
C_ROSE, C_BURGUNDY, C_AMBER, C_BLUE, C_GREEN = "#C97B84", "#7B2D3E", "#EAB676", "#7A9CC6", "#7DB87D"


# ══════════════════════════════════════════════════════════════════════════════
# 1. ÎNCĂRCARE ȘI PREPROCESARE DATE
# ══════════════════════════════════════════════════════════════════════════════

def load_user_data(user_id):
    """Încarcă toate datele utilizatorului prin REST API."""
    endpoints = {
        "tasks":      f"/tasks/user/{user_id}",
        "habits":     f"/habits/user/{user_id}",
        "habit_logs": f"/habits/user/{user_id}/logs",
        "pomodoros":  f"/pomodoro/user/{user_id}",
        "sleep":      f"/sleep/user/{user_id}",
    }
    data = {}
    for key, path in endpoints.items():
        try:
            r = requests.get(BASE_URL + path, timeout=10)
            r.raise_for_status()
            data[key] = r.json()
        except requests.exceptions.ConnectionError:
            print(f"  ❌ Nu mă pot conecta la {BASE_URL}. Pornește backend-ul Spring.")
            sys.exit(1)
        except Exception as e:
            print(f"  ⚠️  Eroare la încărcarea '{key}': {e}")
            data[key] = []
    return data


def build_daily_df(data):
    """
    Construiește un DataFrame cu un rând pe zi activă.
    Coloane: date, tasks, habit_ratio, pomos, focus_min, sleep_hours,
             sleep_quality, weekday, score
    """
    n_habits = max(len(data["habits"]), 1)
    dates = set()

    def acc(d, key, val=1):
        dates.add(d)

    tasks_by_day = {}
    for t in data["tasks"]:
        if t.get("status") == "DONE" and t.get("completedAt"):
            d = t["completedAt"][:10]
            tasks_by_day[d] = tasks_by_day.get(d, 0) + 1
            dates.add(d)

    habits_by_day = {}
    for l in data["habit_logs"]:
        d = l.get("dateCompleted", "")
        if d:
            habits_by_day[d] = habits_by_day.get(d, 0) + 1
            dates.add(d)

    pomos_by_day, focus_by_day = {}, {}
    for p in data["pomodoros"]:
        if p.get("wasCompleted") and p.get("startTime"):
            d = p["startTime"][:10]
            pomos_by_day[d] = pomos_by_day.get(d, 0) + 1
            focus_by_day[d] = focus_by_day.get(d, 0) + p.get("durationMinutes", 0)
            dates.add(d)

    sleep_by_day = {}
    for s in data["sleep"]:
        d = s.get("logDate", "")
        if d and s.get("bedtime") and s.get("wakeUpTime"):
            try:
                bed = pd.to_datetime(s["bedtime"])
                wake = pd.to_datetime(s["wakeUpTime"])
                hours = (wake - bed).total_seconds() / 3600
                if 0 < hours <= 16:
                    sleep_by_day[d] = {"hours": round(hours, 2), "quality": s.get("qualityScore")}
            except Exception:
                pass

    if not dates:
        return pd.DataFrame()

    rows = []
    for d in sorted(dates):
        hd = habits_by_day.get(d, 0)
        hr = hd / n_habits
        T = tasks_by_day.get(d, 0)
        P = pomos_by_day.get(d, 0)
        M = focus_by_day.get(d, 0.0)
        sl = sleep_by_day.get(d, {})

        # Scor brut conform formulei din lucrare: S_brut = 4·T + 30·(H/N_h) + 5·P + 8·(M/60)
        raw = (4 * T) + (30 * hr) + (5 * P) + (8 * M / 60)

        rows.append({
            "date":          d,
            "tasks":         T,
            "habit_ratio":   round(hr, 3),
            "pomos":         P,
            "focus_min":     M,
            "sleep_hours":   sl.get("hours"),
            "sleep_quality": sl.get("quality"),
            "raw_score":     raw,
        })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df["weekday"] = df["date"].dt.dayofweek
    mx = df["raw_score"].max()
    df["score"] = (df["raw_score"] / mx * 100).round(1) if mx > 0 else 0.0
    return df.sort_values("date").reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════════════════
# 2. FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════════════════════════

def engineer_features(df):
    """
    Construiește caracteristicile (features) pentru modelul predictiv.

    Features:
      - sleep_hours_prev, sleep_quality_prev (din noaptea anterioară)
      - dow_sin, dow_cos (codificare ciclică a zilei săptămânii)
      - lag_1, lag_2, lag_3 (scorul ultimelor 3 zile)
      - rolling_3 (media mobilă 3 zile)
      - rolling_7 (media mobilă 7 zile)

    Target: score_next (scorul zilei următoare)
    """
    df = df.copy()

    # Codificare ciclică a zilei săptămânii
    df["dow_sin"] = np.sin(2 * np.pi * df["weekday"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["weekday"] / 7)

    # Lag features (scorul zilelor precedente)
    for k in [1, 2, 3]:
        df[f"lag_{k}"] = df["score"].shift(k)

    # Rolling means
    df["rolling_3"] = df["score"].shift(1).rolling(window=3, min_periods=1).mean()
    df["rolling_7"] = df["score"].shift(1).rolling(window=7, min_periods=1).mean()

    # Sleep features (din noaptea anterioară)
    df["sleep_hours_prev"] = df["sleep_hours"]
    df["sleep_quality_prev"] = df["sleep_quality"]

    # Target: scorul zilei URMĂTOARE
    df["target"] = df["score"].shift(-1)

    feature_cols = [
        "sleep_hours_prev", "sleep_quality_prev",
        "dow_sin", "dow_cos",
        "lag_1", "lag_2", "lag_3",
        "rolling_3", "rolling_7",
        "tasks", "pomos", "habit_ratio",
    ]

    df_ml = df.dropna(subset=feature_cols + ["target"]).reset_index(drop=True)
    return df_ml, feature_cols


# ══════════════════════════════════════════════════════════════════════════════
# 3. MODUL 1 — PREDICȚIA PRODUCTIVITĂȚII (REGRESIE)
# ══════════════════════════════════════════════════════════════════════════════

def train_regression_models(df_ml, feature_cols):
    """
    Antrenează 3 modele de regresie și le compară.
    Returns: dict cu modelele, metricile și predicțiile.
    """
    X = df_ml[feature_cols].values
    y = df_ml["target"].values

    # Train/test split (80/20)
    n = len(df_ml)
    split = int(n * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # Standardizare pentru modelul liniar
    scaler = StandardScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)
    X_test_s = scaler.transform(X_test)

    models = {
        "Ridge Regression":  Ridge(alpha=1.0),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=150, max_depth=4, learning_rate=0.05, random_state=42),
    }

    results = {}
    for name, model in models.items():
        if name == "Ridge Regression":
            model.fit(X_train_s, y_train)
            y_pred = model.predict(X_test_s)
            cv_scores = cross_val_score(model, X_train_s, y_train, cv=KFold(n_splits=5, shuffle=True, random_state=42), scoring="r2")
        else:
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            cv_scores = cross_val_score(model, X_train, y_train, cv=KFold(n_splits=5, shuffle=True, random_state=42), scoring="r2")

        r2 = r2_score(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))

        results[name] = {
            "model":   model,
            "r2":      round(r2, 3),
            "mae":     round(mae, 2),
            "rmse":    round(rmse, 2),
            "cv_mean": round(cv_scores.mean(), 3),
            "cv_std":  round(cv_scores.std(), 3),
            "y_test":  y_test,
            "y_pred":  y_pred,
        }

    # Best model = highest cv_mean
    best_name = max(results, key=lambda k: results[k]["cv_mean"])
    return results, best_name, scaler


def print_regression_report(results, best_name):
    print(f"\n  {'─'*65}")
    print(f"  📊 REZULTATE MODELE DE REGRESIE")
    print(f"  {'─'*65}")
    print(f"  {'Model':<22} {'R²':>8} {'MAE':>8} {'RMSE':>8} {'CV R² (μ±σ)':>18}")
    print(f"  {'─'*65}")
    for name, r in results.items():
        marker = " ⭐" if name == best_name else "   "
        print(f"  {name:<22} {r['r2']:>8} {r['mae']:>8} {r['rmse']:>8} {r['cv_mean']:>10.3f} ± {r['cv_std']:.3f}{marker}")
    print(f"  {'─'*65}")
    print(f"  🏆 Cel mai bun model: {best_name}")


# ══════════════════════════════════════════════════════════════════════════════
# 4. MODUL 2 — CLUSTERING (GRUPAREA COMPORTAMENTALĂ)
# ══════════════════════════════════════════════════════════════════════════════

def run_clustering(df, n_clusters_range=range(2, 8)):
    """
    K-Means clustering cu Elbow + Silhouette.
    """
    feats = ["score", "tasks", "pomos", "habit_ratio", "sleep_hours", "focus_min"]
    df_c = df.dropna(subset=feats).copy()
    if len(df_c) < 10:
        return None

    X = StandardScaler().fit_transform(df_c[feats])

    # Elbow + Silhouette
    wcss, sils = [], []
    for k in n_clusters_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
        wcss.append(km.inertia_)
        sils.append(silhouette_score(X, km.labels_))

    # Best k = max silhouette
    best_k = list(n_clusters_range)[int(np.argmax(sils))]

    # Antrenare model final
    final_km = KMeans(n_clusters=best_k, random_state=42, n_init=10).fit(X)
    labels = final_km.labels_

    # Profilare clustere
    df_c["cluster"] = labels
    profiles = df_c.groupby("cluster")[feats].mean().round(2)

    # Etichete bazate pe scorul mediu
    sorted_clusters = profiles["score"].sort_values(ascending=False)
    cluster_names = {}
    if len(sorted_clusters) == 2:
        cluster_names = {sorted_clusters.index[0]: "Zile productive", sorted_clusters.index[1]: "Zile de odihnă"}
    elif len(sorted_clusters) == 3:
        cluster_names = {sorted_clusters.index[0]: "Deep focus",
                         sorted_clusters.index[1]: "Întreținere",
                         sorted_clusters.index[2]: "Odihnă"}
    else:
        for i, c in enumerate(sorted_clusters.index):
            cluster_names[c] = f"Cluster {i+1}"

    # PCA pentru vizualizare 2D
    pca = PCA(n_components=2)
    X_2d = pca.fit_transform(X)

    return {
        "wcss":          wcss,
        "silhouettes":   sils,
        "k_range":       list(n_clusters_range),
        "best_k":        best_k,
        "labels":        labels,
        "X_2d":          X_2d,
        "df":            df_c,
        "profiles":      profiles,
        "cluster_names": cluster_names,
        "feats":         feats,
        "model":         final_km,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 5. SALVAREA ȘI ÎNCĂRCAREA MODELELOR
# ══════════════════════════════════════════════════════════════════════════════

def save_models(user_id, regression_results, best_name, scaler, feature_cols, cluster_info):
    """Salvează modelele antrenate cu joblib."""
    user_dir = MODELS_DIR / f"user_{user_id}"
    user_dir.mkdir(exist_ok=True)

    # Modelul de regresie (cel mai bun)
    joblib.dump(regression_results[best_name]["model"], user_dir / "regression.pkl")
    joblib.dump(scaler, user_dir / "scaler.pkl")

    # Modelul de clustering (dacă există)
    if cluster_info:
        joblib.dump(cluster_info["model"], user_dir / "clustering.pkl")
        with open(user_dir / "cluster_names.json", "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in cluster_info["cluster_names"].items()}, f, ensure_ascii=False)

    # Metadata
    metadata = {
        "user_id":          user_id,
        "trained_at":       datetime.now().isoformat(),
        "best_model":       best_name,
        "feature_cols":     feature_cols,
        "metrics":          {k: {kk: vv for kk, vv in v.items() if kk in ["r2", "mae", "rmse", "cv_mean", "cv_std"]}
                             for k, v in regression_results.items()},
        "best_cluster_k":   cluster_info["best_k"] if cluster_info else None,
    }
    with open(user_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\n  💾 Modele salvate în: {user_dir}")


def predict_tomorrow(user_id):
    """
    Folosește modelul antrenat ca să prezică scorul de mâine.
    Returnează un dict cu predicția + explicații.
    """
    user_dir = MODELS_DIR / f"user_{user_id}"
    if not (user_dir / "regression.pkl").exists():
        return {"error": f"Nu există model antrenat pentru user_id={user_id}. Rulează --train mai întâi."}

    with open(user_dir / "metadata.json", "r", encoding="utf-8") as f:
        metadata = json.load(f)

    model = joblib.load(user_dir / "regression.pkl")
    scaler = joblib.load(user_dir / "scaler.pkl")

    # Construiește features pentru ziua de azi
    data = load_user_data(user_id)
    df = build_daily_df(data)
    if df.empty:
        return {"error": "Nu există date pentru utilizator."}

    df_ml, feature_cols = engineer_features(df)
    if df_ml.empty:
        return {"error": "Nu există date suficiente pentru predicție."}

    # Ultimul rând disponibil cu toate features-urile
    last_row = df_ml.iloc[-1]
    X_pred = last_row[feature_cols].values.reshape(1, -1)

    # Folosește scaler pentru Ridge
    if metadata["best_model"] == "Ridge Regression":
        X_pred = scaler.transform(X_pred)

    prediction = float(model.predict(X_pred)[0])
    prediction = max(0, min(100, prediction))  # clip 0-100

    # Trend
    recent_avg = df["score"].tail(7).mean()
    trend = "↑" if prediction > recent_avg + 5 else ("↓" if prediction < recent_avg - 5 else "→")

    return {
        "user_id":           user_id,
        "predicted_score":   round(prediction, 1),
        "recent_avg":        round(float(recent_avg), 1),
        "trend":             trend,
        "model_used":        metadata["best_model"],
        "model_r2":          metadata["metrics"][metadata["best_model"]]["cv_mean"],
        "based_on_days":     len(df),
        "predicted_for":     (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 6. GENERAREA RAPOARTELOR PNG (pentru lucrare)
# ══════════════════════════════════════════════════════════════════════════════

def generate_reports(user_id, df, df_ml, feature_cols, regression_results, best_name, cluster_info):
    """Generează grafice de pus în lucrare."""

    # ─── Raport 1: Comparație modele regresie ──────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle(f"Modul 1: Predicția productivității — User {user_id}", color=C_ROSE, fontsize=14, fontweight="bold")

    # Bar chart metrici
    names = list(regression_results.keys())
    r2s = [regression_results[n]["r2"] for n in names]
    maes = [regression_results[n]["mae"] for n in names]
    cv_means = [regression_results[n]["cv_mean"] for n in names]

    ax = axes[0]
    x = np.arange(len(names))
    ax.bar(x - 0.2, r2s, 0.4, label="R² test", color=C_ROSE, alpha=0.85)
    ax.bar(x + 0.2, cv_means, 0.4, label="R² CV", color=C_BURGUNDY, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels([n.replace(" ", "\n") for n in names], fontsize=9)
    ax.set_ylabel("R² Score")
    ax.set_title("Performanța modelelor (R²)", color="#e0d5c8", fontsize=11)
    ax.legend(fontsize=9, facecolor="#1a1a1a", edgecolor="#333")
    ax.grid(axis="y", alpha=0.3)

    # Bar chart MAE
    ax = axes[1]
    ax.bar(names, maes, color=C_AMBER, alpha=0.85)
    ax.set_xticklabels([n.replace(" ", "\n") for n in names], fontsize=9)
    ax.set_ylabel("MAE (puncte)")
    ax.set_title("Eroarea medie absolută (MAE)", color="#e0d5c8", fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    # Predicție vs realitate pentru cel mai bun model
    ax = axes[2]
    r = regression_results[best_name]
    ax.scatter(r["y_test"], r["y_pred"], color=C_ROSE, alpha=0.7, s=50)
    lim = [0, 100]
    ax.plot(lim, lim, color=C_AMBER, linestyle="--", linewidth=1, alpha=0.7, label="Linie ideală")
    ax.set_xlabel("Scor real")
    ax.set_ylabel("Scor prezis")
    ax.set_title(f"Predicție vs. Realitate\n({best_name}, R²={r['r2']})", color="#e0d5c8", fontsize=11)
    ax.legend(fontsize=9, facecolor="#1a1a1a", edgecolor="#333")
    ax.grid(alpha=0.3)
    ax.set_xlim(lim); ax.set_ylim(lim)

    plt.tight_layout()
    out = REPORTS_DIR / f"user_{user_id}_regression.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="#111111")
    plt.close()
    print(f"  📄 {out.name}")

    # ─── Raport 2: Feature importance (pentru modelul nonlinear) ───────────
    if best_name == "Gradient Boosting":
        model = regression_results[best_name]["model"]
        importances = model.feature_importances_
        idx = np.argsort(importances)

        fig, ax = plt.subplots(figsize=(10, 6))
        fig.suptitle(f"Importanța caracteristicilor ({best_name})", color=C_ROSE, fontsize=13, fontweight="bold")
        ax.barh([feature_cols[i] for i in idx], importances[idx], color=C_BURGUNDY, alpha=0.85)
        ax.set_xlabel("Importanță relativă")
        ax.grid(axis="x", alpha=0.3)
        plt.tight_layout()
        out = REPORTS_DIR / f"user_{user_id}_feature_importance.png"
        plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="#111111")
        plt.close()
        print(f"  📄 {out.name}")

    # ─── Raport 3: Clustering ───────────────────────────────────────────────
    if cluster_info:
        fig, axes = plt.subplots(1, 3, figsize=(16, 5))
        fig.suptitle(f"Modul 2: Gruparea comportamentală — User {user_id}", color=C_ROSE, fontsize=14, fontweight="bold")

        # Elbow
        ax = axes[0]
        ax.plot(cluster_info["k_range"], cluster_info["wcss"], color=C_ROSE, marker="o", linewidth=2)
        ax.axvline(cluster_info["best_k"], color=C_AMBER, linestyle="--", alpha=0.7, label=f"k optim = {cluster_info['best_k']}")
        ax.set_xlabel("Număr de clustere (k)")
        ax.set_ylabel("WCSS (inertia)")
        ax.set_title("Metoda Elbow", color="#e0d5c8", fontsize=11)
        ax.legend(fontsize=9, facecolor="#1a1a1a", edgecolor="#333")
        ax.grid(alpha=0.3)

        # Silhouette
        ax = axes[1]
        ax.plot(cluster_info["k_range"], cluster_info["silhouettes"], color=C_BLUE, marker="s", linewidth=2)
        ax.axvline(cluster_info["best_k"], color=C_AMBER, linestyle="--", alpha=0.7, label=f"max la k = {cluster_info['best_k']}")
        ax.set_xlabel("Număr de clustere (k)")
        ax.set_ylabel("Silhouette Score")
        ax.set_title("Scorul Silhouette", color="#e0d5c8", fontsize=11)
        ax.legend(fontsize=9, facecolor="#1a1a1a", edgecolor="#333")
        ax.grid(alpha=0.3)

        # PCA 2D
        ax = axes[2]
        colors = [C_ROSE, C_BURGUNDY, C_AMBER, C_BLUE, C_GREEN, "#9B7EBD", "#FF6B35"]
        for c in range(cluster_info["best_k"]):
            mask = cluster_info["labels"] == c
            label = cluster_info["cluster_names"].get(c, f"Cluster {c}")
            ax.scatter(cluster_info["X_2d"][mask, 0], cluster_info["X_2d"][mask, 1],
                       color=colors[c % len(colors)], alpha=0.7, s=50, label=label)
        ax.set_xlabel("Componenta principală 1")
        ax.set_ylabel("Componenta principală 2")
        ax.set_title(f"Vizualizare PCA (k={cluster_info['best_k']})", color="#e0d5c8", fontsize=11)
        ax.legend(fontsize=8, facecolor="#1a1a1a", edgecolor="#333")
        ax.grid(alpha=0.3)

        plt.tight_layout()
        out = REPORTS_DIR / f"user_{user_id}_clustering.png"
        plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="#111111")
        plt.close()
        print(f"  📄 {out.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 7. MAIN
# ══════════════════════════════════════════════════════════════════════════════

def cmd_train(user_id, generate_reports_flag=True):
    print(f"\n{'═'*65}")
    print(f"  🧠 PRODUCTIVITY INTELLIGENCE ENGINE — Training (User {user_id})")
    print(f"{'═'*65}\n")

    print("  📥 Încarc datele...")
    data = load_user_data(user_id)
    df = build_daily_df(data)
    if df.empty:
        print("  ❌ Nu există date pentru acest utilizator.")
        return
    print(f"     → {len(df)} zile active")

    print("\n  🔧 Feature engineering...")
    df_ml, feature_cols = engineer_features(df)
    print(f"     → {len(df_ml)} mostre, {len(feature_cols)} caracteristici")
    if len(df_ml) < 20:
        print("  ⚠️  Date insuficiente pentru ML serios. Recomandare: minim 30 zile.")

    print("\n  🤖 Modul 1: Antrenare modele de regresie...")
    regression_results, best_name, scaler = train_regression_models(df_ml, feature_cols)
    print_regression_report(regression_results, best_name)

    print("\n  🔬 Modul 2: Gruparea comportamentală (K-Means)...")
    cluster_info = run_clustering(df)
    if cluster_info:
        print(f"     → k optim = {cluster_info['best_k']} clustere (Silhouette = {max(cluster_info['silhouettes']):.3f})")
        print(f"     → Profiluri:")
        for c, name in cluster_info["cluster_names"].items():
            profile = cluster_info["profiles"].loc[c]
            print(f"        • {name}: scor={profile['score']:.0f}, tasks={profile['tasks']:.1f}, "
                  f"pomos={profile['pomos']:.1f}, somn={profile['sleep_hours']:.1f}h")

    save_models(user_id, regression_results, best_name, scaler, feature_cols, cluster_info)

    if generate_reports_flag:
        print("\n  📊 Generare rapoarte PNG...")
        generate_reports(user_id, df, df_ml, feature_cols, regression_results, best_name, cluster_info)

    print(f"\n{'═'*65}")
    print(f"  ✅ Gata! Pentru predicție: python ml_engine.py --user {user_id} --predict")
    print(f"{'═'*65}\n")


def cmd_predict(user_id):
    result = predict_tomorrow(user_id)
    if "error" in result:
        print(f"  ❌ {result['error']}")
        return
    print(f"\n  🔮 Predicție pentru User {user_id} — {result['predicted_for']}:")
    print(f"     Scor estimat: {result['predicted_score']}/100 {result['trend']}")
    print(f"     Media ultimelor 7 zile: {result['recent_avg']}/100")
    print(f"     Model: {result['model_used']} (CV R² = {result['model_r2']})")
    print(f"     Antrenat pe: {result['based_on_days']} zile\n")


def main():
    parser = argparse.ArgumentParser(description="Productivity Intelligence Engine")
    parser.add_argument("--user", type=int, required=True, help="User ID")
    parser.add_argument("--train", action="store_true", help="Antrenează modelele")
    parser.add_argument("--predict", action="store_true", help="Prezice scorul de mâine")
    parser.add_argument("--report", action="store_true", help="Generează rapoarte PNG (necesită --train)")
    parser.add_argument("--no-plot", action="store_true", help="Sări peste graficele PNG")
    args = parser.parse_args()

    if args.train:
        cmd_train(args.user, generate_reports_flag=not args.no_plot)
    elif args.predict:
        cmd_predict(args.user)
    else:
        cmd_train(args.user, generate_reports_flag=True)


if __name__ == "__main__":
    main()
