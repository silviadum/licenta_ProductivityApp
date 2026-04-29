#!/usr/bin/env python3
"""
seed_data.py — Generează date de test realiste pentru ProductivityApp
=====================================================================
Creează 60 de zile de activitate cu PATTERNURI CLARE, astfel încât
scriptul de ML (productivity_insights.py) să poată identifica corelații.

Patternuri embedded:
  • Productivitate mai mare Marți/Miercuri
  • Activitate mai mare dimineața (9-11h) și seara (19-21h)
  • Sesiunile de 25 min au rată de finalizare mai mare decât 60 min
  • Dormit 7-8h → scor mai mare a doua zi
  • Calitate somn corelează cu productivitatea

Rulare:
    python seed_data.py --user 1
    python seed_data.py --user 1 --days 90
    python seed_data.py --user 1 --clear    # șterge datele existente înainte
"""

import argparse
import random
import sys
from datetime import datetime, timedelta, date

import requests

BASE_URL  = "http://localhost:8080/api"
HEADERS   = {"Content-Type": "application/json"}

# ── Patternuri ────────────────────────────────────────────────────────────────

# Probabilitate de activitate per zi (0=Lun … 6=Dum)
DAY_WEIGHTS    = [0.85, 0.95, 0.95, 0.88, 0.80, 0.55, 0.40]

# Distribuție ore pentru completarea task-urilor
TASK_HOURS     = ([9]*20 + [10]*25 + [11]*20 +   # dimineața
                  [14]*10 + [15]*10 +             # după-amiaza
                  [19]*20 + [20]*25 + [21]*15 +   # seara
                  [22]*5  + [23]*3)               # noapte

# Distribuție ore sesiuni Pomodoro
POMO_HOURS     = ([9]*15 + [10]*20 + [11]*15 +
                  [14]*15 + [15]*10 +
                  [19]*20 + [20]*20 + [21]*10 +
                  [22]*5)

# Durate Pomodoro și rata de finalizare per durată
POMO_DURATIONS = [
    (15,  0.95),   # 15 min — aproape mereu finalizate
    (25,  0.90),   # 25 min — finalizate frecvent
    (45,  0.65),   # 45 min — mai greu
    (60,  0.45),   # 60 min — adesea abandonate
]
POMO_DUR_WEIGHTS = [2, 5, 3, 2]   # frecvența de apariție

# ─────────────────────────────────────────────────────────────────────────────

def get(path):
    return requests.get(BASE_URL + path, timeout=8)

def post(path, data):
    return requests.post(BASE_URL + path, json=data, headers=HEADERS, timeout=8)

def put(path, data=None):
    return requests.put(BASE_URL + path, json=data or {}, headers=HEADERS, timeout=8)

def delete(path):
    return requests.delete(BASE_URL + path, timeout=8)

def dt_iso(d: date, hour: int, minute: int = 0) -> str:
    return datetime(d.year, d.month, d.day, hour, minute).isoformat()

def check_backend():
    try:
        requests.get(BASE_URL.replace("/api", ""), timeout=3)
    except Exception:
        print("❌ Nu mă pot conecta la backend. Asigură-te că Spring Boot rulează pe localhost:8080.")
        sys.exit(1)

# ════════════════════════════════════════════════════════════════════════════
# CLEAR (opțional)
# ════════════════════════════════════════════════════════════════════════════

def clear_user_data(user_id):
    print("  🗑️  Șterg datele existente...")
    # tasks
    r = get(f"/tasks/user/{user_id}")
    for t in r.json():
        delete(f"/tasks/{t['id']}")
    # habits (+ logs se șterg automat prin FK sau separat)
    r = get(f"/habits/user/{user_id}")
    for h in r.json():
        delete(f"/habits/{h['id']}")
    # pomodoro
    r = get(f"/pomodoro/user/{user_id}")
    for p in r.json():
        delete(f"/pomodoro/{p['id']}")
    # sleep
    r = get(f"/sleep/user/{user_id}")
    for s in r.json():
        delete(f"/sleep/{s['id']}")
    print("  ✅ Date șterse.")

# ════════════════════════════════════════════════════════════════════════════
# SEED HABITS
# ════════════════════════════════════════════════════════════════════════════

HABIT_NAMES = [
    "Sport / mișcare",
    "Citit 20 minute",
    "Meditație",
    "Fără telefon înainte de somn",
]

def seed_habits(user_id) -> list[dict]:
    print("  🔁 Creez habits...")
    habits = []
    for name in HABIT_NAMES:
        r = post("/habits/add", {"userId": user_id, "name": name})
        if r.status_code == 200:
            habits.append(r.json())
    print(f"     → {len(habits)} habits create")
    return habits

# ════════════════════════════════════════════════════════════════════════════
# SEED TASKS
# ════════════════════════════════════════════════════════════════════════════

TASK_TEMPLATES = [
    ("Rezolvat tema la {subject}", "CLASSIC"),
    ("Studiat capitolul {n} din {subject}", "CLASSIC"),
    ("Proiect {subject} — parte {n}", "CLASSIC"),
    ("Recapitulare {subject}", "QUICK"),
    ("Email profesor {subject}", "QUICK"),
    ("Fișe de studiu {subject}", "QUICK"),
    ("Planificat ziua", "QUICK"),
    ("Organizat note de curs", "QUICK"),
    ("Citit articol despre {subject}", "RADAR"),
    ("Brainstorming {subject}", "RADAR"),
    ("Revizuit obiective săptămânale", "RADAR"),
]
SUBJECTS = ["Matematică", "Programare", "Baze de date", "Rețele", "Algoritmi",
            "Machine Learning", "Sisteme de operare", "Licență"]

def make_title(template):
    subj = random.choice(SUBJECTS)
    n    = random.randint(2, 9)
    return template.format(subject=subj, n=n)

def seed_tasks(user_id, days, start_date) -> list[dict]:
    print("  📋 Creez tasks...")
    created = []
    for offset in range(days):
        d   = start_date + timedelta(days=offset)
        dow = d.weekday()            # 0=Lun
        if random.random() > DAY_WEIGHTS[dow]:
            continue

        # 1-4 tasks per zi activă (mai multe pe zilele bune)
        count = random.choices([1, 2, 3, 4], weights=[15, 40, 30, 15])[0]
        for _ in range(count):
            tpl, typ = random.choice(TASK_TEMPLATES)
            title    = make_title(tpl)
            hour     = random.choice(TASK_HOURS)
            minute   = random.randint(0, 59)
            completed_at = dt_iso(d, hour, minute)

            r = post("/tasks/add", {
                "userId":      user_id,
                "title":       title,
                "type":        typ,
                "status":      "DONE",
                "completedAt": completed_at,
                "xPosition":   random.uniform(15, 85),
                "yPosition":   random.uniform(15, 85),
            })
            if r.status_code == 200:
                created.append(r.json())

    # Câteva tasks TODO (neterminate)
    for _ in range(random.randint(3, 7)):
        tpl, typ = random.choice(TASK_TEMPLATES)
        r = post("/tasks/add", {
            "userId":    user_id,
            "title":     make_title(tpl),
            "type":      typ,
            "status":    "TODO",
            "xPosition": random.uniform(15, 85),
            "yPosition": random.uniform(15, 85),
        })
        if r.status_code == 200:
            created.append(r.json())

    print(f"     → {len(created)} tasks create ({len([t for t in created if t.get('status')=='DONE'])} done, {len([t for t in created if t.get('status')=='TODO'])} todo)")
    return created

# ════════════════════════════════════════════════════════════════════════════
# SEED HABIT LOGS
# ════════════════════════════════════════════════════════════════════════════

def seed_habit_logs(user_id, habits, days, start_date):
    print("  ✅ Loghez habits...")
    count = 0
    for offset in range(days):
        d   = start_date + timedelta(days=offset)
        dow = d.weekday()
        # Rată de bifat: 85% zilele bune, 50% weekend
        rate = 0.85 if dow < 5 else 0.50
        for habit in habits:
            if random.random() < rate:
                r = post(f"/habits/{habit['id']}/log", {"date": d.isoformat()})
                if r.status_code == 200:
                    count += 1
    print(f"     → {count} habit logs create")

# ════════════════════════════════════════════════════════════════════════════
# SEED POMODORO
# ════════════════════════════════════════════════════════════════════════════

def seed_pomodoro(user_id, days, start_date):
    print("  🍅 Creez sesiuni Pomodoro...")
    count = 0
    for offset in range(days):
        d   = start_date + timedelta(days=offset)
        dow = d.weekday()
        if random.random() > DAY_WEIGHTS[dow]:
            continue

        # 1-5 sesiuni per zi activă
        n_sessions = random.choices([1, 2, 3, 4, 5], weights=[15, 30, 30, 15, 10])[0]
        for _ in range(n_sessions):
            dur, completion_rate = random.choices(POMO_DURATIONS, weights=POMO_DUR_WEIGHTS)[0]
            completed = random.random() < completion_rate
            hour      = random.choice(POMO_HOURS)
            minute    = random.randint(0, 55)
            start_iso = dt_iso(d, hour, minute)

            r = post("/pomodoro/add", {
                "userId":          user_id,
                "durationMinutes": dur,
                "wasCompleted":    completed,
                "startTime":       start_iso,
            })
            if r.status_code == 200:
                count += 1

    print(f"     → {count} sesiuni Pomodoro create")

# ════════════════════════════════════════════════════════════════════════════
# SEED SLEEP
# ════════════════════════════════════════════════════════════════════════════

def sleep_quality(hours: float) -> int:
    """Calitate corelată cu orele dormite + zgomot."""
    base = min(10, max(1, int((hours - 4) * 2.2)))
    return max(1, min(10, base + random.randint(-1, 1)))

def seed_sleep(user_id, days, start_date):
    print("  😴 Loghez somnul...")
    count = 0
    for offset in range(days):
        log_date = start_date + timedelta(days=offset)
        # 90% din zile au date de somn
        if random.random() > 0.90:
            continue

        # Ore dormite: distribuție normală în jurul a 7h
        hours = max(4.0, min(10.0, random.gauss(7.2, 1.1)))

        # Ora de culcare — dacă >= 7h atunci se culcă la ~23:00, altfel mai târziu
        if hours >= 7:
            bed_h = random.choices([22, 23, 0], weights=[30, 50, 20])[0]
        else:
            bed_h = random.choices([0, 1, 2], weights=[40, 40, 20])[0]
        bed_m = random.randint(0, 59)

        # Bedtime e în seara anterioară dacă ora >= 20
        bed_date = log_date - timedelta(days=1) if bed_h >= 20 else log_date
        bedtime_iso = dt_iso(bed_date, bed_h, bed_m)

        # Ora de trezire
        wake_total_min = bed_h * 60 + bed_m + int(hours * 60)
        wake_h = (wake_total_min // 60) % 24
        wake_m = wake_total_min % 60
        wake_iso = dt_iso(log_date, wake_h, wake_m)

        r = post("/sleep/add", {
            "userId":       user_id,
            "bedtime":      bedtime_iso,
            "wakeUpTime":   wake_iso,
            "qualityScore": sleep_quality(hours),
            "logDate":      log_date.isoformat(),
        })
        if r.status_code == 200:
            count += 1

    print(f"     → {count} nopți de somn logate")

# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Seed data pentru ProductivityApp ML")
    parser.add_argument("--user",  type=int, default=1,  help="User ID (default: 1)")
    parser.add_argument("--days",  type=int, default=60, help="Câte zile de date să generezi (default: 60)")
    parser.add_argument("--clear", action="store_true",  help="Șterge datele existente înainte de generare")
    args = parser.parse_args()

    print(f"\n{'═'*55}")
    print(f"  🌱 SEED DATA — User {args.user} · {args.days} zile")
    print(f"{'═'*55}")

    check_backend()

    if args.clear:
        clear_user_data(args.user)

    start_date = date.today() - timedelta(days=args.days)
    print(f"  Perioadă: {start_date} → {date.today()}\n")

    habits = seed_habits(args.user)
    seed_tasks(args.user, args.days, start_date)
    seed_habit_logs(args.user, habits, args.days, start_date)
    seed_pomodoro(args.user, args.days, start_date)
    seed_sleep(args.user, args.days, start_date)

    print(f"\n{'═'*55}")
    print(f"  ✅ Gata! Acum rulează analiza ML:")
    print(f"     python productivity_insights.py --user {args.user}")
    print(f"{'═'*55}\n")

if __name__ == "__main__":
    main()
