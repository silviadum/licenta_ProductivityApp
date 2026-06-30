#!/usr/bin/env python3
"""
ml_engine.py — Productivity Intelligence Engine (CLASSIFICATION-BASED)
=======================================================================
Pipeline de Machine Learning pentru ProductivityApp:

  Predicția productivității (CLASIFICARE supervizată 3-clase):
    - Țintă: ziua DE AZI e SLABĂ (<40) / NORMALĂ (40-70) / BUNĂ (>70)
    - Features: activitate din ZIUA PRECEDENTĂ + somn din noaptea trecută
                + ziua săptămânii (azi) + lag features istoric
    - Logistic Regression (regularizat L2)
    - Random Forest Classifier (ensemble)
    - Feature engineering: lag features, rolling mean, cyclical encoding
    - Evaluare: accuracy, precision/recall/F1 per clasă, ROC-AUC (1-vs-rest)
               + k-fold cross-validation + confusion matrix

Rulare:
    python ml_engine.py --user 4 --train        # antrenează și salvează modelul
    python ml_engine.py --user 4 --predict      # prezice clasa zilei de azi
"""

import argparse
import json
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
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, confusion_matrix,
    f1_score, precision_score, recall_score, roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler, label_binarize
from xgboost import XGBClassifier

import optuna
from scipy.optimize import minimize_scalar
optuna.logging.set_verbosity(optuna.logging.WARNING)

warnings.filterwarnings("ignore")

# ─── Configurare ─────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8080/api"
MODELS_DIR = Path(__file__).parent / "models"
REPORTS_DIR = Path(__file__).parent / "reports"
MODELS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Clase pentru clasificare
CLASS_NAMES = ["SLABA", "NORMALA", "BUNA"]
CLASS_LABELS_RO = ["Slaba", "Normala", "Buna"]
CLASS_THRESHOLDS = [40, 70]   # < 40 = SLABA, 40-70 = NORMALA, > 70 = BUNA

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
            print(f"  ❌ Nu mă pot conecta la {BASE_URL}. Porneste backend-ul Spring.")
            sys.exit(1)
        except Exception as e:
            print(f"  ⚠️  Eroare la încărcarea '{key}': {e}")
            data[key] = []
    return data


def build_daily_df(data):
    """Construiește un DataFrame cu un rând pe zi activă."""
    n_habits = max(len(data["habits"]), 1)
    dates = set()

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

        # Scor brut: S = 4·T + 30·(H/N_h) + 5·P + 8·(M/60)
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
    # Normalizare robustă: folosesc percentila 95 în loc de max pentru a evita outlier-ii
    mx = df["raw_score"].quantile(0.95)
    df["score"] = (df["raw_score"] / mx * 100).clip(0, 100).round(1) if mx > 0 else 0.0
    return df.sort_values("date").reset_index(drop=True)


def categorize_score(score):
    """Convertește scor numeric → clasă: SLABA (0) / NORMALA (1) / BUNA (2)."""
    if score < CLASS_THRESHOLDS[0]:
        return 0  # SLABA
    if score <= CLASS_THRESHOLDS[1]:
        return 1  # NORMALA
    return 2  # BUNA


# ══════════════════════════════════════════════════════════════════════════════
# 2. FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════════════════════════

def engineer_features(df):
    """
    Construiește vectorul EXTINS de caracteristici (29 features).

    Organizat pe orizonturi temporale:
      ── CONTEXT IMEDIAT (original, 12 features) ─────────────────────
        * sleep_hours_prev / sleep_quality_prev
        * dow_sin / dow_cos
        * lag_1, lag_2, lag_3
        * rolling_3, rolling_7
        * tasks_yesterday, pomos_yesterday, habit_ratio_yesterday

      ── CATEGORIA A: BASELINE PERSONAL ──────────────────────────────
        * baseline_30d, baseline_lifetime
        * deviation_yesterday, deviation_3d_avg

      ── CATEGORIA B: DIRECȚIE PE TERMEN LUNG ────────────────────────
        * trend_30d, week_change, ewma_score

      ── CATEGORIA C: TIPARE SĂPTĂMÂNALE PERSONALIZATE ──────────────
        * this_dow_avg_4w, this_dow_avg_lifetime

      ── CATEGORIA D: VOLATILITATE / CONSISTENȚĂ ────────────────────
        * score_std_30d, sleep_std_30d

      ── CATEGORIA E: STREAK / MOMENTUM ──────────────────────────────
        * current_good_streak, days_since_last_bad

      ── INTERACȚIUNI ȘI SEZONALITATE ────────────────────────────────
        * sleep_x_habits, focus_x_sleep_quality
        * month_sin, month_cos, is_weekend

    Target: clasa scorului DE AZI (SLABA / NORMALA / BUNA).
    Toate features-urile folosesc DOAR informații din trecut (shift 1).
    """
    df = df.copy()

    # Score shifted = scorurile fără ziua curentă (evită data leakage)
    score_shifted = df["score"].shift(1)

    # ── CONTEXT IMEDIAT (păstrate din versiunea originală) ────────────
    df["dow_sin"] = np.sin(2 * np.pi * df["weekday"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["weekday"] / 7)
    for k in [1, 2, 3]:
        df[f"lag_{k}"] = df["score"].shift(k)
    df["rolling_3"] = score_shifted.rolling(window=3, min_periods=1).mean()
    df["rolling_7"] = score_shifted.rolling(window=7, min_periods=1).mean()
    df["sleep_hours_prev"] = df["sleep_hours"]
    df["sleep_quality_prev"] = df["sleep_quality"]
    df["tasks_yesterday"] = df["tasks"].shift(1)
    df["pomos_yesterday"] = df["pomos"].shift(1)
    df["habit_ratio_yesterday"] = df["habit_ratio"].shift(1)

    # ══════════════════════════════════════════════════════════════════
    # CATEGORIA A — BASELINE PERSONAL
    # ══════════════════════════════════════════════════════════════════
    # Baseline 30 zile: media scorurilor din ultimele 30 zile
    df["baseline_30d"] = score_shifted.rolling(window=30, min_periods=7).mean()
    # Baseline lifetime: media expansibilă din toate zilele anterioare
    df["baseline_lifetime"] = score_shifted.expanding(min_periods=7).mean()
    # Deviația scorului de ieri vs baseline 30d
    df["deviation_yesterday"] = df["lag_1"] - df["baseline_30d"]
    # Deviația mediei ultimelor 3 zile vs baseline 30d
    df["deviation_3d_avg"] = df["rolling_3"] - df["baseline_30d"]

    # ══════════════════════════════════════════════════════════════════
    # CATEGORIA B — DIRECȚIE PE TERMEN LUNG
    # ══════════════════════════════════════════════════════════════════
    # Trend 30d: panta liniei de regresie pe ultimele 30 zile
    def _slope(window):
        valid = window.dropna()
        if len(valid) < 5:
            return np.nan
        x = np.arange(len(valid), dtype=float)
        try:
            slope, _ = np.polyfit(x, valid.values, 1)
            return slope
        except Exception:
            return np.nan

    df["trend_30d"] = score_shifted.rolling(window=30, min_periods=5).apply(
        _slope, raw=False
    )
    # Week change: medie săptămâna trecută vs sub-anterioară
    mean_last_7d = score_shifted.rolling(window=7, min_periods=3).mean()
    mean_prev_7d = score_shifted.shift(7).rolling(window=7, min_periods=3).mean()
    df["week_change"] = mean_last_7d - mean_prev_7d
    # EWMA: medie exponențial ponderată (halflife = 7 zile)
    df["ewma_score"] = score_shifted.ewm(halflife=7, min_periods=3).mean()

    # ══════════════════════════════════════════════════════════════════
    # CATEGORIA C — TIPARE SĂPTĂMÂNALE PERSONALIZATE
    # ══════════════════════════════════════════════════════════════════
    def _dow_avg(df_inner, lookback_days):
        """Pentru fiecare zi, media scorurilor pentru același DOW în trecut."""
        result = np.full(len(df_inner), np.nan)
        weekdays = df_inner["weekday"].values
        scores = df_inner["score"].values
        for i in range(len(df_inner)):
            current_dow = weekdays[i]
            start_idx = max(0, i - lookback_days) if lookback_days else 0
            mask_dow = weekdays[start_idx:i] == current_dow
            relevant = scores[start_idx:i][mask_dow]
            relevant = relevant[~np.isnan(relevant)]
            if len(relevant) > 0:
                result[i] = relevant.mean()
        return result

    df["this_dow_avg_4w"] = _dow_avg(df, lookback_days=28)
    df["this_dow_avg_lifetime"] = _dow_avg(df, lookback_days=None)

    # ══════════════════════════════════════════════════════════════════
    # CATEGORIA D — VOLATILITATE / CONSISTENȚĂ
    # ══════════════════════════════════════════════════════════════════
    df["score_std_30d"] = score_shifted.rolling(window=30, min_periods=7).std()
    df["sleep_std_30d"] = df["sleep_hours"].shift(1).rolling(window=30, min_periods=7).std()

    # ══════════════════════════════════════════════════════════════════
    # CATEGORIA E — STREAK / MOMENTUM
    # ══════════════════════════════════════════════════════════════════
    # Current good streak: zile consecutive (înainte de azi) cu scor > 50
    is_good = (score_shifted > 50).fillna(False).astype(int)
    streak_id = (is_good == 0).cumsum()
    df["current_good_streak"] = is_good.groupby(streak_id).cumsum()

    # Days since last bad day (scor < 40)
    is_bad = (score_shifted < 40).fillna(False).astype(bool)
    idx_arr = np.arange(len(df), dtype=float)
    last_bad_idx = np.where(is_bad.values, idx_arr, np.nan)
    last_bad_filled = pd.Series(last_bad_idx).ffill().values
    days_since = idx_arr - last_bad_filled
    df["days_since_last_bad"] = pd.Series(days_since).fillna(999).values

    # ══════════════════════════════════════════════════════════════════
    # INTERACȚIUNI
    # ══════════════════════════════════════════════════════════════════
    df["sleep_x_habits"] = df["sleep_hours_prev"] * df["habit_ratio_yesterday"]
    df["focus_x_sleep_quality"] = df["pomos_yesterday"] * df["sleep_quality_prev"]

    # ══════════════════════════════════════════════════════════════════
    # SEZONALITATE
    # ══════════════════════════════════════════════════════════════════
    df["month_sin"] = np.sin(2 * np.pi * df["date"].dt.month / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["date"].dt.month / 12)
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)

    # Target: clasa scorului DE AZI
    df["target"] = df["score"].apply(lambda x: categorize_score(x) if pd.notna(x) else np.nan)

    feature_cols = [
        # ─── CONTEXT IMEDIAT (12) ───
        "sleep_hours_prev", "sleep_quality_prev",
        "dow_sin", "dow_cos",
        "lag_1", "lag_2", "lag_3",
        "rolling_3", "rolling_7",
        "tasks_yesterday", "pomos_yesterday", "habit_ratio_yesterday",
        # ─── CATEGORIA A: Baseline personal (4) ───
        "baseline_30d", "baseline_lifetime",
        "deviation_yesterday", "deviation_3d_avg",
        # ─── CATEGORIA B: Direcție pe termen lung (3) ───
        "trend_30d", "week_change", "ewma_score",
        # ─── CATEGORIA C: Tipare săptămânale personalizate (2) ───
        "this_dow_avg_4w", "this_dow_avg_lifetime",
        # ─── CATEGORIA D: Volatilitate (2) ───
        "score_std_30d", "sleep_std_30d",
        # ─── CATEGORIA E: Streak / Momentum (2) ───
        "current_good_streak", "days_since_last_bad",
        # ─── Interacțiuni (2) ───
        "sleep_x_habits", "focus_x_sleep_quality",
        # ─── Sezonalitate (3) ───
        "month_sin", "month_cos", "is_weekend",
    ]

    df_ml = df.dropna(subset=feature_cols + ["target"]).reset_index(drop=True)
    df_ml["target"] = df_ml["target"].astype(int)
    return df_ml, feature_cols


# ══════════════════════════════════════════════════════════════════════════════
# 3. CLASIFICARE 3-CLASE
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# Hyperparameter tuning cu Optuna (Bayesian Optimization)
# ══════════════════════════════════════════════════════════════════════════════

def tune_xgboost(X_train, y_train, cv, n_trials=40):
    """Bayesian optimization pentru XGBoost folosind Tree-structured Parzen Estimator."""
    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 100, 400),
            'max_depth': trial.suggest_int('max_depth', 3, 9),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.25, log=True),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'reg_alpha': trial.suggest_float('reg_alpha', 1e-3, 5, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 1e-3, 5, log=True),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 8),
            'gamma': trial.suggest_float('gamma', 0, 2),
        }
        model = XGBClassifier(
            **params, objective='multi:softprob', num_class=3,
            eval_metric='mlogloss', tree_method='hist',
            random_state=42, n_jobs=-1,
        )
        # Sample weights pentru class imbalance
        class_counts = np.bincount(y_train)
        weights = len(y_train) / (len(class_counts) * class_counts)
        sample_w = weights[y_train]
        # CV manuala ca sa putem trece sample_weight la fit
        scores = []
        for tr_idx, va_idx in cv.split(X_train):
            m = XGBClassifier(
                **params, objective='multi:softprob', num_class=3,
                eval_metric='mlogloss', tree_method='hist',
                random_state=42, n_jobs=-1,
            )
            m.fit(X_train[tr_idx], y_train[tr_idx], sample_weight=sample_w[tr_idx])
            pred = m.predict(X_train[va_idx])
            scores.append(f1_score(y_train[va_idx], pred, average='macro', zero_division=0))
        return float(np.mean(scores))

    sampler = optuna.samplers.TPESampler(seed=42)
    study = optuna.create_study(direction='maximize', sampler=sampler)
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return study.best_params, study.best_value


def tune_random_forest(X_train, y_train, cv, n_trials=30):
    """Bayesian optimization pentru Random Forest."""
    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 100, 400),
            'max_depth': trial.suggest_int('max_depth', 4, 15),
            'min_samples_split': trial.suggest_int('min_samples_split', 2, 15),
            'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 8),
            'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', None]),
        }
        model = RandomForestClassifier(
            **params, class_weight='balanced', random_state=42, n_jobs=-1,
        )
        scores = cross_val_score(
            model, X_train, y_train, cv=cv, scoring='f1_macro', n_jobs=1,
        )
        return scores.mean()

    sampler = optuna.samplers.TPESampler(seed=42)
    study = optuna.create_study(direction='maximize', sampler=sampler)
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return study.best_params, study.best_value


# ══════════════════════════════════════════════════════════════════════════════
# Threshold tuning per clasă (maximizează F1 macro)
# ══════════════════════════════════════════════════════════════════════════════

def tune_thresholds(y_true, y_proba, n_iter=10):
    """
    Tunează thresholds per clasă prin coordinate descent ca să maximizeze F1 macro.
    În loc de argmax(proba), folosim argmax(proba / threshold).

    Asta permite modelului să fie mai sensibil la clase rare (SLABA).
    """
    n_classes = y_proba.shape[1]
    thresholds = np.ones(n_classes) / n_classes  # init uniform

    def apply_thresholds(thr):
        adj = y_proba / thr
        return np.argmax(adj, axis=1)

    def f1_at(thr):
        return f1_score(y_true, apply_thresholds(thr), average='macro', zero_division=0)

    best_f1 = f1_at(thresholds)
    for it in range(n_iter):
        improved = False
        for c in range(n_classes):
            def neg_f1(t, c=c, base=thresholds.copy()):
                base[c] = t
                return -f1_at(base)
            result = minimize_scalar(neg_f1, bounds=(0.05, 0.95), method='bounded',
                                     options={'xatol': 1e-3})
            if -result.fun > best_f1 + 1e-4:
                thresholds[c] = result.x
                best_f1 = -result.fun
                improved = True
        if not improved:
            break

    return thresholds, best_f1


def train_classification_models(df_ml, feature_cols):
    """
    Antrenează 3 modele de clasificare și le compară:
      - Logistic Regression (baseline liniar)
      - Random Forest Classifier (ensemble bagging)
      - XGBoost (gradient boosting — standard pentru date tabelare)

    Cross-validation: TimeSeriesSplit (respectă ordinea cronologică,
    elimină data leakage din viitor).

    Criteriu de selectie compus:
        score = 0.5 * cv_accuracy + 0.5 * cv_f1_macro

    Folosesc F1 macro (nu weighted) ca sa penalizez modelele care
    colapseaza pe clasa majoritara. Modelele care prezic doar NORMALA
    obtin un F1 macro mic, indiferent de acuratete.
    """
    X = df_ml[feature_cols].values
    y = df_ml["target"].values

    # Train/test split (80/20) temporal — testul = ultimele 20% zile
    n = len(df_ml)
    split = int(n * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # Standardizare pentru Logistic Regression
    scaler = StandardScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)
    X_test_s = scaler.transform(X_test)

    # TimeSeriesSplit pentru CV onest pe serii temporale
    tscv = TimeSeriesSplit(n_splits=5)

    # Sample weights pentru XGBoost (compenseaza dezechilibrul claselor)
    class_counts = np.bincount(y_train)
    class_weights = len(y_train) / (len(class_counts) * class_counts)
    sample_weights = class_weights[y_train]

    models = {
        "Logistic Regression": LogisticRegression(
            max_iter=2000, C=0.5, random_state=42, class_weight="balanced",
            solver="lbfgs",
        ),
        "Random Forest Classifier": RandomForestClassifier(
            n_estimators=200, max_depth=8, min_samples_leaf=3,
            random_state=42, class_weight="balanced", n_jobs=-1,
        ),
        "XGBoost": XGBClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.07,
            subsample=0.85, colsample_bytree=0.85, reg_lambda=1.5,
            objective="multi:softprob", num_class=3,
            random_state=42, eval_metric="mlogloss",
            tree_method="hist", n_jobs=-1,
        ),
    }

    results = {}
    for name, model in models.items():
        # Standardizare doar pentru LR
        Xtr, Xte = (X_train_s, X_test_s) if name == "Logistic Regression" else (X_train, X_test)

        if name == "XGBoost":
            model.fit(Xtr, y_train, sample_weight=sample_weights)
        else:
            model.fit(Xtr, y_train)

        y_pred = model.predict(Xte)
        y_proba = model.predict_proba(Xte)

        # CV cu TimeSeriesSplit pe accuracy si f1_macro separat
        cv_acc = cross_val_score(model, Xtr, y_train, cv=tscv, scoring="accuracy")
        cv_f1 = cross_val_score(model, Xtr, y_train, cv=tscv, scoring="f1_macro")

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
        rec = recall_score(y_test, y_pred, average="weighted", zero_division=0)
        f1w = f1_score(y_test, y_pred, average="weighted", zero_division=0)
        f1m = f1_score(y_test, y_pred, average="macro", zero_division=0)

        # ROC-AUC multi-class (one-vs-rest)
        try:
            unique_classes = np.unique(y_test)
            if len(unique_classes) >= 2 and y_proba.shape[1] >= len(unique_classes):
                y_test_bin = label_binarize(y_test, classes=[0, 1, 2])
                if y_test_bin.shape[1] == y_proba.shape[1]:
                    auc = roc_auc_score(y_test_bin, y_proba, average="weighted", multi_class="ovr")
                else:
                    auc = None
            else:
                auc = None
        except Exception:
            auc = None

        cm = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])

        # Scor compus pentru selectie
        composite = 0.5 * cv_acc.mean() + 0.5 * cv_f1.mean()

        results[name] = {
            "model":    model,
            "accuracy": round(acc, 3),
            "precision": round(prec, 3),
            "recall":   round(rec, 3),
            "f1":       round(f1w, 3),
            "f1_macro": round(f1m, 3),
            "auc":      round(auc, 3) if auc is not None else None,
            "cv_mean":  round(cv_acc.mean(), 3),
            "cv_std":   round(cv_acc.std(), 3),
            "cv_f1_macro": round(cv_f1.mean(), 3),
            "composite_score": round(composite, 3),
            "y_test":   y_test,
            "y_pred":   y_pred,
            "y_proba":  y_proba,
            "confusion_matrix": cm.tolist(),
        }

    # Best model = scorul compus cel mai mare (CV accuracy + F1 macro)
    best_name = max(results, key=lambda k: results[k]["composite_score"])
    return results, best_name, scaler


def print_classification_report(results, best_name):
    print(f"\n  {'─'*92}")
    print(f"  📊 REZULTATE MODELE DE CLASIFICARE (3 clase: SLABA / NORMALA / BUNA)")
    print(f"  {'─'*92}")
    print(f"  {'Model':<26} {'Acc':>6} {'Prec':>6} {'Rec':>6} {'F1w':>6} {'F1m':>6} {'AUC':>6} {'CVAcc':>10} {'CVF1m':>6} {'Score':>7}")
    print(f"  {'─'*92}")
    for name, r in results.items():
        marker = " ⭐" if name == best_name else "   "
        auc_str = f"{r['auc']:.3f}" if r['auc'] is not None else "N/A"
        print(f"  {name:<26} {r['accuracy']:>6.3f} {r['precision']:>6.3f} {r['recall']:>6.3f} {r['f1']:>6.3f} "
              f"{r['f1_macro']:>6.3f} {auc_str:>6} {r['cv_mean']:>5.3f}±{r['cv_std']:.2f} {r['cv_f1_macro']:>6.3f} "
              f"{r['composite_score']:>7.3f}{marker}")
    print(f"  {'─'*92}")
    print(f"  🏆 Cel mai bun model (scor compus 0.5*CVAcc + 0.5*CVF1macro): {best_name}")

    # Confusion matrix detaliată
    best_cm = np.array(results[best_name]["confusion_matrix"])
    print(f"\n  Confusion Matrix ({best_name}):")
    print(f"            Pred:  SLABA  NORMALA  BUNA")
    for i, row_label in enumerate(CLASS_NAMES):
        print(f"  Real {row_label:>8}:   {best_cm[i][0]:>4}    {best_cm[i][1]:>4}     {best_cm[i][2]:>4}")

    # Feature importance pentru tree-based models
    best_model = results[best_name]["model"]
    if hasattr(best_model, "feature_importances_"):
        print(f"\n  📈 Top 10 features (importance, {best_name}):")
        return best_model.feature_importances_
    return None

    # Feature importance pentru tree-based models
    best_model = results[best_name]["model"]
    if hasattr(best_model, "feature_importances_"):
        print(f"\n  📈 Top 10 features (importance, {best_name}):")
        # Nota: importances sunt in ordinea feature_cols
        # Le vom afișa în main, unde avem acces și la feature_cols
        return best_model.feature_importances_
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 4. SALVAREA ȘI ÎNCĂRCAREA MODELELOR
# ══════════════════════════════════════════════════════════════════════════════

def save_models(user_id, classification_results, best_name, scaler, feature_cols):
    """Salvează modelele antrenate cu joblib."""
    user_dir = MODELS_DIR / f"user_{user_id}"
    user_dir.mkdir(exist_ok=True)

    # Salvează cel mai bun clasificator
    joblib.dump(classification_results[best_name]["model"], user_dir / "classifier.pkl")
    joblib.dump(scaler, user_dir / "scaler.pkl")

    # Metadata
    metadata = {
        "user_id":          user_id,
        "trained_at":       datetime.now().isoformat(),
        "task_type":        "classification",
        "n_classes":        3,
        "class_names":      CLASS_NAMES,
        "class_thresholds": CLASS_THRESHOLDS,
        "best_model":       best_name,
        "feature_cols":     feature_cols,
        "metrics":          {k: {kk: vv for kk, vv in v.items()
                                 if kk in ["accuracy", "precision", "recall", "f1", "auc", "cv_mean", "cv_std", "confusion_matrix"]}
                             for k, v in classification_results.items()},
    }
    with open(user_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\n  💾 Modele salvate in: {user_dir}")


def predict_today(user_id):
    """Folosește clasificatorul antrenat ca să prezică CLASA zilei de AZI."""
    user_dir = MODELS_DIR / f"user_{user_id}"
    if not (user_dir / "classifier.pkl").exists():
        return {"error": f"Nu exista model antrenat pentru user_id={user_id}. Ruleaza --train mai intai."}

    with open(user_dir / "metadata.json", "r", encoding="utf-8") as f:
        metadata = json.load(f)

    model = joblib.load(user_dir / "classifier.pkl")
    scaler = joblib.load(user_dir / "scaler.pkl")

    data = load_user_data(user_id)
    df = build_daily_df(data)
    if df.empty:
        return {"error": "Nu exista date pentru utilizator."}

    df_ml, feature_cols = engineer_features(df)
    if df_ml.empty:
        return {"error": "Nu exista date suficiente pentru predictie."}

    # Folosim ultima linie disponibilă (cea mai recentă zi) — features-urile sunt construite
    # exclusiv pe baza zilelor ANTERIOARE (lag, rolling, activitate ieri), deci predicția
    # se aplică zilei curente fără să folosească date pe care nu le-am avea încă.
    last_row = df_ml.iloc[-1]
    X_pred = last_row[feature_cols].values.reshape(1, -1)

    if metadata["best_model"] == "Logistic Regression":
        X_pred = scaler.transform(X_pred)

    pred_class = int(model.predict(X_pred)[0])
    pred_proba = model.predict_proba(X_pred)[0]

    return {
        "user_id":           user_id,
        "predicted_class":   CLASS_NAMES[pred_class],
        "predicted_label":   CLASS_LABELS_RO[pred_class],
        "confidence":        round(float(pred_proba[pred_class]), 3),
        "probabilities":     {CLASS_NAMES[i]: round(float(pred_proba[i]), 3) for i in range(len(CLASS_NAMES))},
        "model_used":        metadata["best_model"],
        "model_accuracy":    metadata["metrics"][metadata["best_model"]]["cv_mean"],
        "based_on_days":     len(df),
        "predicted_for":     datetime.now().strftime("%Y-%m-%d"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 5. GENERAREA RAPOARTELOR PNG
# ══════════════════════════════════════════════════════════════════════════════

def generate_reports(user_id, df_ml, feature_cols, classification_results, best_name):
    """Generează grafice pentru lucrare."""

    # ─── Raport 1: Comparație modele + Confusion Matrix ─────────────────────
    fig = plt.figure(figsize=(16, 10), facecolor="#111111")
    fig.suptitle(f"Clasificare 3-clase — User {user_id}", color=C_ROSE, fontsize=14, fontweight="bold")

    # Bar chart cu metrici
    ax = plt.subplot(2, 2, 1)
    names = list(classification_results.keys())
    x = np.arange(len(names))
    metrics_to_plot = ["accuracy", "precision", "recall", "f1"]
    colors_metrics = [C_ROSE, C_BURGUNDY, C_AMBER, C_GREEN]
    width = 0.18
    for i, m in enumerate(metrics_to_plot):
        vals = [classification_results[n][m] for n in names]
        ax.bar(x + i*width - 1.5*width, vals, width, label=m.capitalize(), color=colors_metrics[i], alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels([n.replace(" ", "\n") for n in names], fontsize=9)
    ax.set_ylabel("Scor")
    ax.set_title("Performanța modelelor", color="#e0d5c8", fontsize=11)
    ax.legend(fontsize=8, facecolor="#1a1a1a", edgecolor="#333", labelcolor="#e0d5c8")
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, 1.05)

    # CV accuracy comparison
    ax = plt.subplot(2, 2, 2)
    cv_means = [classification_results[n]["cv_mean"] for n in names]
    cv_stds = [classification_results[n]["cv_std"] for n in names]
    bars = ax.bar(names, cv_means, yerr=cv_stds, color=C_BURGUNDY, alpha=0.85, capsize=8, ecolor=C_AMBER)
    ax.set_xticklabels([n.replace(" ", "\n") for n in names], fontsize=9)
    ax.set_ylabel("Accuracy CV (5-fold)")
    ax.set_title("Cross-validation stability", color="#e0d5c8", fontsize=11)
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, 1.05)

    # Confusion matrix pentru cel mai bun model
    ax = plt.subplot(2, 2, 3)
    best_cm = np.array(classification_results[best_name]["confusion_matrix"])
    im = ax.imshow(best_cm, cmap="RdPu", aspect="auto", interpolation="nearest")
    ax.set_xticks(range(3))
    ax.set_yticks(range(3))
    ax.set_xticklabels(CLASS_NAMES, color="#e0d5c8")
    ax.set_yticklabels(CLASS_NAMES, color="#e0d5c8")
    ax.set_xlabel("Predict", color="#e0d5c8")
    ax.set_ylabel("Real", color="#e0d5c8")
    ax.set_title(f"Confusion Matrix ({best_name})", color="#e0d5c8", fontsize=11)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, str(best_cm[i][j]), ha="center", va="center",
                    color="white" if best_cm[i][j] > best_cm.max()/2 else "black", fontsize=12, fontweight="bold")

    # Distribuția claselor în datele de antrenare
    ax = plt.subplot(2, 2, 4)
    classes_dist = pd.Series(df_ml["target"]).value_counts().sort_index()
    class_labels = [CLASS_NAMES[i] for i in classes_dist.index]
    colors_classes = [C_BLUE, C_AMBER, C_GREEN]
    ax.bar(class_labels, classes_dist.values, color=colors_classes, alpha=0.85)
    ax.set_ylabel("Numar de zile")
    ax.set_title("Distribuție clase în date", color="#e0d5c8", fontsize=11)
    ax.grid(axis="y", alpha=0.3)
    for i, v in enumerate(classes_dist.values):
        ax.text(i, v + 1, str(v), ha="center", color="#e0d5c8", fontsize=10)

    plt.tight_layout()
    out = REPORTS_DIR / f"user_{user_id}_classification.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="#111111")
    plt.close()
    print(f"  📄 {out.name}")

    # ─── Raport 2: Feature importance ────────────────────────────────────────
    if best_name == "Random Forest Classifier":
        model = classification_results[best_name]["model"]
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

    # ─── Raport 3: ROC curves ────────────────────────────────────────────────
    n_models = len(classification_results)
    fig, axes = plt.subplots(1, n_models, figsize=(7 * n_models, 5))
    if n_models == 1:
        axes = [axes]
    fig.suptitle("Curbe ROC (one-vs-rest) pentru fiecare clasa", color=C_ROSE, fontsize=13, fontweight="bold")

    for idx, (name, r) in enumerate(classification_results.items()):
        ax = axes[idx]
        y_test = r["y_test"]
        y_proba = r["y_proba"]
        y_test_bin = label_binarize(y_test, classes=[0, 1, 2])

        colors_roc = [C_BLUE, C_AMBER, C_GREEN]
        for i, class_name in enumerate(CLASS_NAMES):
            if i < y_proba.shape[1] and y_test_bin.shape[1] > i:
                try:
                    fpr, tpr, _ = roc_curve(y_test_bin[:, i], y_proba[:, i])
                    auc_i = roc_auc_score(y_test_bin[:, i], y_proba[:, i])
                    ax.plot(fpr, tpr, color=colors_roc[i], lw=2,
                            label=f"{class_name} (AUC={auc_i:.2f})")
                except Exception:
                    pass

        ax.plot([0, 1], [0, 1], color="#555", linestyle="--", alpha=0.5)
        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("True Positive Rate")
        ax.set_title(name, color="#e0d5c8", fontsize=11)
        ax.legend(fontsize=9, facecolor="#1a1a1a", edgecolor="#333", labelcolor="#e0d5c8")
        ax.grid(alpha=0.3)

    plt.tight_layout()
    out = REPORTS_DIR / f"user_{user_id}_roc_curves.png"
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="#111111")
    plt.close()
    print(f"  📄 {out.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 6. MAIN
# ══════════════════════════════════════════════════════════════════════════════

def cmd_train(user_id, generate_reports_flag=True):
    print(f"\n{'═'*65}")
    print(f"  🧠 PRODUCTIVITY INTELLIGENCE ENGINE — Training (User {user_id})")
    print(f"     Mod: CLASIFICARE 3-clase (SLABA / NORMALA / BUNA)")
    print(f"{'═'*65}\n")

    print("  📥 Incarc datele...")
    data = load_user_data(user_id)
    df = build_daily_df(data)
    if df.empty:
        print("  ❌ Nu exista date pentru acest utilizator.")
        return
    print(f"     → {len(df)} zile active")

    print("\n  🔧 Feature engineering...")
    df_ml, feature_cols = engineer_features(df)
    print(f"     → {len(df_ml)} mostre, {len(feature_cols)} caracteristici")

    # Distribuția claselor
    class_dist = pd.Series(df_ml["target"]).value_counts().sort_index()
    print(f"     → Distribuție clase:")
    for cls_idx, count in class_dist.items():
        print(f"        • {CLASS_NAMES[cls_idx]}: {count} zile ({100*count/len(df_ml):.1f}%)")

    if len(df_ml) < 20:
        print("  ⚠️  Date insuficiente pentru ML serios. Recomandare: minim 30 zile.")

    print("\n  🤖 Antrenare modele de clasificare...")
    classification_results, best_name, scaler = train_classification_models(df_ml, feature_cols)
    importances = print_classification_report(classification_results, best_name)

    if importances is not None:
        top_idx = np.argsort(importances)[::-1][:10]
        for rank, idx in enumerate(top_idx, 1):
            print(f"     {rank:>2}. {feature_cols[idx]:<28} {importances[idx]:.4f}")

    save_models(user_id, classification_results, best_name, scaler, feature_cols)

    if generate_reports_flag:
        print("\n  📊 Generare rapoarte PNG...")
        generate_reports(user_id, df_ml, feature_cols, classification_results, best_name)

    print(f"\n{'═'*65}")
    print(f"  ✅ Gata! Pentru predictie: python ml_engine.py --user {user_id} --predict")
    print(f"{'═'*65}\n")


def cmd_predict(user_id):
    result = predict_today(user_id)
    if "error" in result:
        print(f"  ❌ {result['error']}")
        return
    print(f"\n  🔮 Predictie AZI pentru User {user_id} — {result['predicted_for']}:")
    print(f"     Clasa estimata: {result['predicted_label']} ({result['predicted_class']})")
    print(f"     Increderea: {result['confidence']*100:.1f}%")
    print(f"     Probabilitati:")
    for cls, prob in result['probabilities'].items():
        print(f"        • {cls}: {prob*100:.1f}%")
    print(f"     Model: {result['model_used']} (CV Accuracy = {result['model_accuracy']})")
    print(f"     Antrenat pe: {result['based_on_days']} zile\n")


def main():
    parser = argparse.ArgumentParser(description="Productivity Intelligence Engine (Classification)")
    parser.add_argument("--user", type=int, required=True, help="User ID")
    parser.add_argument("--train", action="store_true", help="Antreneaza modelele")
    parser.add_argument("--predict", action="store_true", help="Prezice clasa zilei DE AZI")
    parser.add_argument("--no-plot", action="store_true", help="Sari peste graficele PNG")
    args = parser.parse_args()

    if args.train:
        cmd_train(args.user, generate_reports_flag=not args.no_plot)
    elif args.predict:
        cmd_predict(args.user)
    else:
        cmd_train(args.user, generate_reports_flag=True)


if __name__ == "__main__":
    main()
