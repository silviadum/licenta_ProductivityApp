#!/usr/bin/env python3
"""
Productivity Insights — Analiză ML pentru ProductivityApp
=========================================================
Răspunde la întrebări de tipul:
  • Ești mai productiv dimineața sau seara?
  • În ce zile ale săptămânii produci cel mai mult?
  • Sesiunile de 25 min sau de 45 min îți aduc mai multe rezultate?
  • Când dormi 7 ore vs 9 ore, ce se schimbă?
  • Există o corelație între calitatea somnului și productivitate?

Rulare:
    python productivity_insights.py --user 1
    python productivity_insights.py --user 1 --no-plot   # doar text
    python productivity_insights.py --user 1 --save      # salvează PNG
"""

import argparse
import sys
import warnings
from datetime import datetime

import matplotlib
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from scipy import stats

warnings.filterwarnings("ignore")

# ── Temă vizuală (matching app-ul) ──────────────────────────────────────────
matplotlib.rcParams.update({
    "figure.facecolor":  "#111111",
    "axes.facecolor":    "#1a1a1a",
    "text.color":        "#e0d5c8",
    "axes.labelcolor":   "#e0d5c8",
    "xtick.color":       "#888888",
    "ytick.color":       "#888888",
    "axes.edgecolor":    "#333333",
    "grid.color":        "#2a2a2a",
    "grid.alpha":        1.0,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "font.family":       "sans-serif",
})

C_BURGUNDY = "#7B2D3E"
C_ROSE     = "#C97B84"
C_NUDE     = "#E0D5C8"
C_OFFBLACK = "#111111"
C_AMBER    = "#EAB676"
C_BLUE     = "#7A9CC6"
C_MUTED    = "#444444"

BASE_URL = "http://localhost:8080/api"

WEEKDAY_MAP = {
    "Monday": "Luni", "Tuesday": "Marți", "Wednesday": "Miercuri",
    "Thursday": "Joi", "Friday": "Vineri", "Saturday": "Sâmbătă", "Sunday": "Duminică",
}
WEEKDAY_SHORT = ["L", "Ma", "Mi", "J", "V", "S", "D"]


# ════════════════════════════════════════════════════════════════════════════
# 1. ÎNCĂRCARE DATE DE LA REST API
# ════════════════════════════════════════════════════════════════════════════

def load_data(user_id: int) -> dict:
    """Preia toate datele de la backend pentru user-ul specificat."""
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
            resp = requests.get(BASE_URL + path, timeout=8)
            resp.raise_for_status()
            data[key] = resp.json()
        except requests.exceptions.ConnectionError:
            print(f"  [EROARE] Nu mă pot conecta la {BASE_URL}. Asigură-te că backend-ul rulează.")
            sys.exit(1)
        except Exception as exc:
            print(f"  [WARN] Nu s-a putut încărca '{key}': {exc}")
            data[key] = []
    return data


# ════════════════════════════════════════════════════════════════════════════
# 2. TRANSFORMARE DATE → DataFrame-uri
# ════════════════════════════════════════════════════════════════════════════

def time_block(hour: int) -> str:
    if 5 <= hour < 12:  return "Dimineață (5-12)"
    if 12 <= hour < 17: return "După-amiază (12-17)"
    if 17 <= hour < 22: return "Seară (17-22)"
    return "Noapte (22-5)"


def build_daily_df(data: dict) -> pd.DataFrame:
    """
    Un rând per zi activă.
    Coloane: date, tasks_done, habit_ratio, pomo_sessions, pomo_minutes,
             sleep_hours, sleep_quality, productivity_score, weekday, weekday_name
    """
    n_habits = len(data["habits"])
    dates = set()

    # tasks completate → data
    task_by_day: dict[str, int] = {}
    for t in data["tasks"]:
        if t.get("status") == "DONE" and t.get("completedAt"):
            d = t["completedAt"][:10]
            task_by_day[d] = task_by_day.get(d, 0) + 1
            dates.add(d)

    # habit logs → data
    habit_by_day: dict[str, int] = {}
    for l in data["habit_logs"]:
        d = l.get("dateCompleted", "")
        if d:
            habit_by_day[d] = habit_by_day.get(d, 0) + 1
            dates.add(d)

    # pomodoro sessions (doar completate) → data
    pomo_sessions: dict[str, int]   = {}
    pomo_minutes:  dict[str, float] = {}
    for p in data["pomodoros"]:
        if p.get("wasCompleted") and p.get("startTime"):
            d = p["startTime"][:10]
            pomo_sessions[d] = pomo_sessions.get(d, 0) + 1
            pomo_minutes[d]  = pomo_minutes.get(d, 0) + p.get("durationMinutes", 0)
            dates.add(d)

    # sleep logs → data (indexate pe logDate)
    sleep_by_day: dict[str, dict] = {}
    for s in data["sleep"]:
        d = s.get("logDate", "")
        if d:
            try:
                bed  = pd.to_datetime(s.get("bedtime"))
                wake = pd.to_datetime(s.get("wakeUpTime"))
                h = (wake - bed).total_seconds() / 3600
                sleep_by_day[d] = {
                    "hours":   round(h, 2) if h > 0 else None,
                    "quality": s.get("qualityScore"),
                }
            except Exception:
                pass
            dates.add(d)

    if not dates:
        return pd.DataFrame()

    rows = []
    for d in sorted(dates):
        hd = habit_by_day.get(d, 0)
        hr = hd / n_habits if n_habits > 0 else 0.0
        ps = pomo_sessions.get(d, 0)
        pm = pomo_minutes.get(d, 0.0)
        sl = sleep_by_day.get(d, {})

        # Scor brut: task-uri 40%, habits 30%, pomodoro 30%
        score = (task_by_day.get(d, 0) * 4) + (hr * 30) + (ps * 5) + (pm / 60 * 8)
        rows.append({
            "date":          d,
            "tasks_done":    task_by_day.get(d, 0),
            "habit_ratio":   round(hr, 3),
            "pomo_sessions": ps,
            "pomo_minutes":  pm,
            "sleep_hours":   sl.get("hours"),
            "sleep_quality": sl.get("quality"),
            "raw_score":     score,
        })

    df = pd.DataFrame(rows)
    df["date"]         = pd.to_datetime(df["date"])
    df["weekday"]      = df["date"].dt.dayofweek          # 0 = Luni
    df["weekday_name"] = df["date"].dt.day_name()

    # Normalizare scor 0-100
    mx = df["raw_score"].max()
    df["productivity_score"] = (df["raw_score"] / mx * 100).round(1) if mx > 0 else 0.0

    return df


def build_pomo_df(data: dict) -> pd.DataFrame:
    """Un rând per sesiune pomodoro."""
    rows = []
    for p in data["pomodoros"]:
        if not p.get("startTime"):
            continue
        dt = pd.to_datetime(p["startTime"])
        rows.append({
            "date":       dt.date().isoformat(),
            "hour":       dt.hour,
            "duration":   p.get("durationMinutes", 25),
            "completed":  bool(p.get("wasCompleted", False)),
            "time_block": time_block(dt.hour),
        })
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(columns=["date", "hour", "duration", "completed", "time_block"])


def build_task_df(data: dict) -> pd.DataFrame:
    """Un rând per task completat (include ora finalizării)."""
    rows = []
    for t in data["tasks"]:
        if t.get("status") == "DONE" and t.get("completedAt"):
            dt = pd.to_datetime(t["completedAt"])
            rows.append({
                "date":       dt.date().isoformat(),
                "hour":       dt.hour,
                "time_block": time_block(dt.hour),
            })
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(columns=["date", "hour", "time_block"])


# ════════════════════════════════════════════════════════════════════════════
# 3. GENERARE INSIGHTS TEXT
# ════════════════════════════════════════════════════════════════════════════

def generate_insights(daily: pd.DataFrame, pomo: pd.DataFrame, tasks: pd.DataFrame) -> list[str]:
    insights = []

    if daily.empty:
        return ["Nu există date suficiente pentru analiză. Adaugă mai multe activități."]

    # ── Interval orar cel mai productiv ─────────────────────────────────────
    events = []
    if not tasks.empty:
        events.extend(tasks["time_block"].tolist())
    if not pomo.empty:
        events.extend(pomo[pomo["completed"]]["time_block"].tolist())
    if events:
        block_counts = pd.Series(events).value_counts()
        best = block_counts.idxmax()
        pct  = block_counts.max() / block_counts.sum() * 100
        insights.append(f"⏰  Ești cel mai activ {best} ({pct:.0f}% din activitate)")

    # ── Ziua săptămânii ──────────────────────────────────────────────────────
    if len(daily) >= 5:
        day_avg = (
            daily.groupby("weekday_name")["productivity_score"]
            .mean()
            .rename(index=WEEKDAY_MAP)
        )
        best_day  = day_avg.idxmax()
        worst_day = day_avg.idxmin()
        insights.append(
            f"📅  Ziua ta cea mai productivă: {best_day} "
            f"(scor mediu {day_avg.max():.0f}/100)"
        )
        insights.append(
            f"😴  Ziua cu cel mai mic scor: {worst_day} "
            f"(scor mediu {day_avg.min():.0f}/100)"
        )

    # ── Durata Pomodoro ──────────────────────────────────────────────────────
    if not pomo.empty and len(pomo) >= 4:
        done = pomo[pomo["completed"]]
        if not done.empty:
            short = pomo[pomo["duration"] <= 25]
            long_ = pomo[pomo["duration"] >= 40]
            if len(short) >= 2 and len(long_) >= 2:
                rate_s = short["completed"].mean() * 100
                rate_l = long_["completed"].mean() * 100
                winner = "scurte (≤25 min)" if rate_s >= rate_l else "lungi (≥40 min)"
                r_w    = max(rate_s, rate_l)
                r_l    = min(rate_s, rate_l)
                insights.append(
                    f"⏱️  Sesiunile {winner} îți merg mai bine "
                    f"(finalizare {r_w:.0f}% vs {r_l:.0f}%)"
                )
            avg_dur = done["duration"].mean()
            insights.append(f"🍅  Durata medie a sesiunilor finalizate: {avg_dur:.0f} min")

    # ── Ore somn → productivitate ────────────────────────────────────────────
    sleep_df = daily[daily["sleep_hours"].notna()].copy()
    if len(sleep_df) >= 4:
        sleep_df["sleep_cat"] = pd.cut(
            sleep_df["sleep_hours"],
            bins=[0, 6, 7, 8, 9, 24],
            labels=["<6h", "6-7h", "7-8h", "8-9h", ">9h"],
        )
        cat_scores = (
            sleep_df.groupby("sleep_cat", observed=True)["productivity_score"]
            .mean()
            .dropna()
        )
        if len(cat_scores) > 1:
            best_sl = cat_scores.idxmax()
            insights.append(
                f"😴  Cel mai productiv ești când dormi {best_sl} "
                f"(scor mediu {cat_scores.max():.0f}/100)"
            )

        # Corelație ore → scor
        corr, pval = stats.pearsonr(sleep_df["sleep_hours"], sleep_df["productivity_score"])
        if abs(corr) > 0.15:
            sens = "pozitivă" if corr > 0 else "negativă"
            insights.append(
                f"📈  Corelație ore somn ↔ productivitate: {corr:+.2f} ({sens})"
            )

    # ── Calitate somn → productivitate ──────────────────────────────────────
    q_df = daily[daily["sleep_quality"].notna()].copy()
    if len(q_df) >= 4:
        q_corr, _ = stats.pearsonr(q_df["sleep_quality"], q_df["productivity_score"])
        if abs(q_corr) > 0.15:
            sens = "crește" if q_corr > 0 else "scade"
            insights.append(
                f"⭐  Calitate somn ↔ productivitate: r={q_corr:+.2f} — "
                f"productivitatea {sens} odată cu calitatea somnului"
            )

    # ── Rată habits ──────────────────────────────────────────────────────────
    if len(daily) >= 5:
        avg_hr = daily["habit_ratio"].mean() * 100
        insights.append(f"🔁  Rată medie de completare habits: {avg_hr:.0f}%")

    # ── Trend general ────────────────────────────────────────────────────────
    if len(daily) >= 7:
        first_half = daily["productivity_score"].iloc[: len(daily) // 2].mean()
        second_half = daily["productivity_score"].iloc[len(daily) // 2 :].mean()
        diff = second_half - first_half
        if abs(diff) > 3:
            direction = "în creștere 📈" if diff > 0 else "în scădere 📉"
            insights.append(
                f"🏁  Productivitatea ta este {direction} "
                f"(+{diff:+.1f} puncte față de începuturi)"
            )

    return insights if insights else ["Adaugă mai multe date pentru a genera insight-uri."]


# ════════════════════════════════════════════════════════════════════════════
# 4. VIZUALIZARE
# ════════════════════════════════════════════════════════════════════════════

def _ax_no_data(ax, title: str):
    ax.set_facecolor("#1a1a1a")
    ax.text(0.5, 0.5, "date\ninsuficiente", ha="center", va="center",
            color=C_MUTED, fontsize=9, transform=ax.transAxes)
    ax.set_title(title, color=C_NUDE, fontsize=10, pad=8)
    ax.set_xticks([])
    ax.set_yticks([])


def plot_insights(
    daily: pd.DataFrame,
    pomo:  pd.DataFrame,
    tasks: pd.DataFrame,
    user_id: int,
    save: bool = False,
):
    if daily.empty:
        print("Nu există date suficiente pentru grafice.")
        return

    fig = plt.figure(figsize=(17, 12), facecolor=C_OFFBLACK)
    fig.suptitle(
        f"Productivity Insights — User {user_id}",
        fontsize=17, color=C_ROSE, fontweight="bold", y=0.99,
    )

    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.58, wspace=0.42)

    # ── [0,0:2] Activitate per oră a zilei ───────────────────────────────────
    ax_hour = fig.add_subplot(gs[0, :2])
    hour_counts = [0] * 24
    for _, r in (tasks.iterrows() if not tasks.empty else pd.DataFrame().iterrows()):
        hour_counts[int(r["hour"])] += 1
    for _, r in (pomo[pomo["completed"]].iterrows() if not pomo.empty else pd.DataFrame().iterrows()):
        hour_counts[int(r["hour"])] += 0.6  # sesiunile cântăresc puțin mai puțin

    max_val = max(hour_counts) if max(hour_counts) > 0 else 1
    clrs = [C_ROSE if v == max_val else C_BURGUNDY for v in hour_counts]
    ax_hour.bar(range(24), hour_counts, color=clrs, alpha=0.88, width=0.8)

    # zone colorate subtile
    for (s, e, c) in [(5,12,"#ffffff"),(12,17,"#ffffff"),(17,22,"#ffffff"),(22,24,"#aaaaff"),(0,5,"#aaaaff")]:
        ax_hour.axvspan(s, e, alpha=0.03, color=c)
    for x, lbl in [(5,"Dimineață"),(12,"După-amiază"),(17,"Seară"),(22,"Noapte")]:
        ax_hour.axvline(x, color="#333", linewidth=0.8, linestyle="--")
        ax_hour.text(x + 0.3, max_val * 0.92, lbl, color="#555", fontsize=7)

    ax_hour.set_title("Activitate per oră (tasks + pomodoro)", color=C_NUDE, fontsize=10, pad=8)
    ax_hour.set_xlabel("Ora", fontsize=9)
    ax_hour.set_ylabel("Activități", fontsize=9)
    ax_hour.set_xticks(range(0, 24, 2))
    ax_hour.set_xticklabels([f"{h}:00" for h in range(0, 24, 2)], fontsize=7, rotation=45)
    ax_hour.grid(axis="y", alpha=0.3)

    # ── [0,2] Scor per zi a săptămânii ───────────────────────────────────────
    ax_day = fig.add_subplot(gs[0, 2])
    if len(daily) >= 3:
        day_avg = daily.groupby("weekday")["productivity_score"].mean()
        lbls  = [WEEKDAY_SHORT[i] for i in day_avg.index]
        clrs  = [C_ROSE if v == day_avg.max() else C_BURGUNDY for v in day_avg.values]
        ax_day.bar(lbls, day_avg.values, color=clrs, alpha=0.88)
        ax_day.set_title("Scor mediu per zi", color=C_NUDE, fontsize=10, pad=8)
        ax_day.set_ylabel("Scor (/100)", fontsize=9)
        ax_day.grid(axis="y", alpha=0.3)
        ax_day.set_ylim(0, 105)
    else:
        _ax_no_data(ax_day, "Scor per zi")

    # ── [1,0] Durata Pomodoro vs sesiuni finalizate ───────────────────────────
    ax_pomo = fig.add_subplot(gs[1, 0])
    if not pomo.empty and len(pomo) >= 3:
        done_pomo = pomo[pomo["completed"]].copy()
        done_pomo["dur_cat"] = pd.cut(
            done_pomo["duration"],
            bins=[0, 20, 30, 45, 200],
            labels=["≤20 min", "21-30 min", "31-45 min", ">45 min"],
        )
        dur_cnt = done_pomo.groupby("dur_cat", observed=True).size()
        clrs = [C_AMBER if v == dur_cnt.max() else "#6b4c20" for v in dur_cnt.values]
        ax_pomo.bar(dur_cnt.index.astype(str), dur_cnt.values, color=clrs, alpha=0.88)
        ax_pomo.set_title("Sesiuni finalizate\nper durată", color=C_NUDE, fontsize=10, pad=8)
        ax_pomo.set_ylabel("Sesiuni", fontsize=9)
        ax_pomo.grid(axis="y", alpha=0.3)
        # rata de completare per categorie
        all_pomo = pomo.copy()
        all_pomo["dur_cat"] = pd.cut(
            all_pomo["duration"], bins=[0, 20, 30, 45, 200],
            labels=["≤20 min", "21-30 min", "31-45 min", ">45 min"],
        )
        rates = all_pomo.groupby("dur_cat", observed=True)["completed"].mean() * 100
        for i, (cat, rate) in enumerate(rates.items()):
            if cat in dur_cnt.index:
                ax_pomo.text(i, dur_cnt.get(cat, 0) + 0.1, f"{rate:.0f}%",
                             ha="center", va="bottom", fontsize=8, color=C_NUDE)
    else:
        _ax_no_data(ax_pomo, "Durata Pomodoro")

    # ── [1,1] Ore somn → Productivitate ──────────────────────────────────────
    ax_sleep = fig.add_subplot(gs[1, 1])
    sleep_df = daily[daily["sleep_hours"].notna()].copy()
    if len(sleep_df) >= 4:
        sleep_df["sleep_cat"] = pd.cut(
            sleep_df["sleep_hours"],
            bins=[0, 6, 7, 8, 9, 24],
            labels=["<6h", "6-7h", "7-8h", "8-9h", ">9h"],
        )
        cat_sc = sleep_df.groupby("sleep_cat", observed=True)["productivity_score"].mean()
        cnt    = sleep_df.groupby("sleep_cat", observed=True).size()
        clrs   = [C_BLUE if v == cat_sc.max() else "#3a5a7a" for v in cat_sc.values]
        ax_sleep.bar(cat_sc.index.astype(str), cat_sc.values, color=clrs, alpha=0.88)
        # anotare cu nr nopți
        for i, (cat, sc) in enumerate(cat_sc.items()):
            n = cnt.get(cat, 0)
            ax_sleep.text(i, sc + 0.5, f"n={n}", ha="center", va="bottom",
                          fontsize=7, color="#777")
        ax_sleep.set_title("Ore somn →\nProductivitate a doua zi", color=C_NUDE, fontsize=10, pad=8)
        ax_sleep.set_xlabel("Ore dormite", fontsize=9)
        ax_sleep.set_ylabel("Scor mediu (/100)", fontsize=9)
        ax_sleep.grid(axis="y", alpha=0.3)
        ax_sleep.set_ylim(0, 108)
    else:
        _ax_no_data(ax_sleep, "Ore somn → Productivitate")

    # ── [1,2] Calitate somn → Productivitate ─────────────────────────────────
    ax_qual = fig.add_subplot(gs[1, 2])
    q_df = daily[daily["sleep_quality"].notna()].copy()
    if len(q_df) >= 4:
        q_sc = q_df.groupby("sleep_quality")["productivity_score"].mean()
        ax_qual.bar(q_sc.index.astype(str), q_sc.values, color=C_BLUE, alpha=0.6)
        # trend line
        if len(q_sc) >= 3:
            xs = np.array(q_sc.index, dtype=float)
            ys = q_sc.values
            z  = np.polyfit(xs, ys, 1)
            p  = np.poly1d(z)
            x_cont = np.linspace(1, 10, 100)
            ax_qual.plot(
                [str(int(x)) if x == int(x) else "" for x in range(1, 11)],
                [p(i) for i in range(1, 11)],
                color=C_ROSE, linewidth=2, linestyle="--", alpha=0.85, label=f"Trend",
            )
            ax_qual.legend(fontsize=7, facecolor="#1a1a1a", edgecolor="#333",
                           labelcolor=C_NUDE, framealpha=0.8)
        ax_qual.set_title("Calitate somn →\nProductivitate", color=C_NUDE, fontsize=10, pad=8)
        ax_qual.set_xlabel("Calitate (1-10)", fontsize=9)
        ax_qual.set_ylabel("Scor mediu (/100)", fontsize=9)
        ax_qual.grid(axis="y", alpha=0.3)
    else:
        _ax_no_data(ax_qual, "Calitate somn → Productivitate")

    # ── [2,0:2] Trend productivitate în timp ─────────────────────────────────
    ax_trend = fig.add_subplot(gs[2, :2])
    if len(daily) >= 3:
        x   = np.arange(len(daily))
        y   = daily["productivity_score"].values
        ax_trend.fill_between(x, y, alpha=0.25, color=C_BURGUNDY)
        ax_trend.plot(x, y, color=C_ROSE, linewidth=1.8, zorder=3)

        # rolling average 7 zile
        if len(daily) >= 7:
            roll = daily["productivity_score"].rolling(7, min_periods=3).mean()
            ax_trend.plot(x, roll.values, color=C_AMBER, linewidth=1.5,
                          linestyle="--", alpha=0.9, label="Medie mobilă 7z")

        # trend liniar
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        ax_trend.plot(x, p(x), color=C_BLUE, linewidth=1,
                      linestyle=":", alpha=0.7, label="Trend liniar")

        ax_trend.set_title("Evoluție productivitate în timp", color=C_NUDE, fontsize=10, pad=8)
        ax_trend.set_ylabel("Scor productivitate (/100)", fontsize=9)

        # etichete pe axa X: la fiecare ~6 zile
        step = max(1, len(daily) // 7)
        ticks = list(range(0, len(daily), step))
        ax_trend.set_xticks(ticks)
        ax_trend.set_xticklabels(
            [daily.iloc[i]["date"].strftime("%d %b") for i in ticks],
            fontsize=8, rotation=30,
        )
        ax_trend.legend(fontsize=8, facecolor="#1a1a1a", edgecolor="#333",
                        labelcolor=C_NUDE, framealpha=0.8)
        ax_trend.grid(alpha=0.25)
        ax_trend.set_ylim(0, 115)
    else:
        _ax_no_data(ax_trend, "Evoluție în timp")

    # ── [2,2] Insights text ───────────────────────────────────────────────────
    ax_ins = fig.add_subplot(gs[2, 2])
    ax_ins.set_facecolor("#151515")
    ax_ins.axis("off")
    ax_ins.set_title("💡 Insights", color=C_ROSE, fontsize=10,
                     fontweight="bold", pad=10, loc="left")

    insights = generate_insights(daily, pomo, tasks)
    txt = "\n\n".join(f"• {i}" for i in insights[:6])
    ax_ins.text(
        0.05, 0.92, txt,
        fontsize=8, color=C_NUDE,
        transform=ax_ins.transAxes,
        va="top", linespacing=1.65,
        wrap=True,
    )

    plt.tight_layout(rect=[0, 0, 1, 0.97])

    if save:
        fname = f"productivity_insights_user{user_id}.png"
        plt.savefig(fname, dpi=150, bbox_inches="tight", facecolor=C_OFFBLACK)
        print(f"\n  ✅ Grafic salvat: {fname}")

    plt.show()


# ════════════════════════════════════════════════════════════════════════════
# 5. MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Productivity Insights — analiză ML pentru ProductivityApp"
    )
    parser.add_argument("--user",    type=int, default=1, help="User ID (default: 1)")
    parser.add_argument("--no-plot", action="store_true",  help="Afișează doar text, fără fereastră grafică")
    parser.add_argument("--save",    action="store_true",  help="Salvează graficul ca PNG")
    args = parser.parse_args()

    print(f"\n{'═'*60}")
    print(f"  🔍  PRODUCTIVITY INSIGHTS — User {args.user}")
    print(f"{'═'*60}")
    print(f"  Se preia date de la {BASE_URL} ...")

    data = load_data(args.user)

    totals = {k: len(v) for k, v in data.items()}
    print(f"\n  Date preluate:")
    print(f"    Tasks:       {totals['tasks']}")
    print(f"    Habits:      {totals['habits']}")
    print(f"    Habit logs:  {totals['habit_logs']}")
    print(f"    Pomodoro:    {totals['pomodoros']}")
    print(f"    Sleep logs:  {totals['sleep']}")

    if sum(totals.values()) == 0:
        print("\n  ❌ Nicio dată găsită. Adaugă activități în aplicație mai întâi.")
        sys.exit(0)

    daily  = build_daily_df(data)
    pomo   = build_pomo_df(data)
    tasks  = build_task_df(data)

    print(f"\n  Zile active analizate: {len(daily)}\n")
    print(f"{'─'*60}")
    print(f"  INSIGHTS:")
    print(f"{'─'*60}")
    for ins in generate_insights(daily, pomo, tasks):
        print(f"  {ins}")
    print(f"{'═'*60}\n")

    if not args.no_plot:
        plot_insights(daily, pomo, tasks, args.user, save=args.save)


if __name__ == "__main__":
    main()
