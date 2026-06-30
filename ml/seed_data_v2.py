#!/usr/bin/env python3
"""
seed_data_v2.py — Generator de date sintetice cu tipare comportamentale realiste
==============================================================================
Spre deosebire de versiunea v1 (care folosea aleatoriu independent pentru fiecare
dimensiune), aceasta versiune modeleaza un "utilizator persona" cu:

  • Energie zilnica care depinde de somnul nopti precedente
  • Momentum (o zi buna creste sansa unei zile bune urmatoare)
  • Ritm saptamanal (luni recuperare, marti-mier varf, vineri declin)
  • Doua perioade de burnout (1 saptamana fiecare) pe parcursul anului
  • Trend usor ascendent pe termen lung (utilizatorul se imbunatateste)
  • Preferinta personala pentru sesiuni Pomodoro de 25 min
  • Corelatie sleep_quality <-> sleep_hours cu zgomot natural
  • Variabilitate naturala (zile-anomalie ~5%)

Tiparele sunt INTENTIONAT realiste, nu artificial puternice. Modelul ML va
invata ce poate, dar nu va putea sa prezica perfect (ca in lumea reala).

Rulare:
    python seed_data_v2.py --user 2 --clear
    python seed_data_v2.py --user 3 --days 400
"""

import argparse
import math
import random
import sys
from datetime import datetime, timedelta, date

import requests

BASE_URL = "http://localhost:8080/api"
HEADERS  = {"Content-Type": "application/json"}


# ════════════════════════════════════════════════════════════════════════════
# MODELUL PERSOANEI: ENERGIE ZILNICA
# ════════════════════════════════════════════════════════════════════════════

class PersonaModel:
    """
    Modeleaza un utilizator cu tipare realiste de productivitate.

    Energia zilnica (in [0, 1]) este factorul principal care influenteaza
    cate task-uri / pomos / obiceiuri va face si cu ce rata de finalizare.
    """

    # Ponderi pe zile saptamanii (0=Lun ... 6=Dum) — ritm natural
    # Luni: recuperare dupa weekend, Marti-Mier: varf, Joi: usor in jos,
    # Vineri: declin, Weekend: relax
    WEEKDAY_BIAS = [0.78, 0.95, 0.97, 0.88, 0.75, 0.55, 0.50]

    # Preferinta personala pentru durate Pomodoro
    POMO_DURATIONS = [15, 25, 45, 60]
    # Rata de finalizare la energia maxima — utilizatorul prefera 25min
    POMO_BASE_COMPLETION = {15: 0.92, 25: 0.85, 45: 0.55, 60: 0.35}
    # Frecventa cu care alege fiecare durata
    POMO_FREQUENCY = {15: 0.15, 25: 0.50, 45: 0.25, 60: 0.10}

    def __init__(self, seed: int, total_days: int):
        self.rng = random.Random(seed)
        self.total_days = total_days
        # Perioade de burnout (1 saptamana fiecare)
        self.burnout_periods = self._pick_burnout_periods()
        # Energia de ieri (pentru momentum) - initial neutra
        self.prev_energy = 0.55

    def _pick_burnout_periods(self):
        """Alege 2 perioade de burnout de 7 zile, distantate."""
        windows = []
        # Prima fereastra: zilele 60-90
        start1 = self.rng.randint(60, 90)
        windows.append((start1, start1 + 7))
        # A doua fereastra: zilele 200-250 (mid-pana-spre-final)
        start2 = self.rng.randint(200, 250)
        windows.append((start2, start2 + 7))
        return windows

    def _is_burnout(self, day_idx: int) -> bool:
        return any(s <= day_idx < e for s, e in self.burnout_periods)

    def _long_term_trend(self, day_idx: int) -> float:
        """Trend ascendent usor: utilizatorul se imbunatateste cu ~5 puncte
        pe parcursul anului (max +0.05 la energie)."""
        return 0.05 * (day_idx / self.total_days)

    def sleep_hours(self, day_idx: int, dow: int, prev_was_short: bool) -> float:
        """Ore de somn realiste cu recovery dupa noapte scurta."""
        # Baseline ~7.5h, weekend +0.5h
        base = 7.5 + (0.5 if dow >= 5 else 0)
        # Recovery dupa noapte scurta
        if prev_was_short:
            base += 0.8
        # Cu probabilitate mica: noapte scurta (insomnie, deadline, etc)
        if self.rng.random() < 0.07:
            return max(4.0, self.rng.gauss(5.5, 0.5))
        # Burnout = somn mai prost
        if self._is_burnout(day_idx):
            base -= 0.5
        # Zgomot natural
        hours = self.rng.gauss(base, 0.8)
        return max(4.0, min(10.5, hours))

    def sleep_quality(self, hours: float, day_idx: int) -> int:
        """Calitate corelata cu orele dormite + zgomot natural."""
        # Functie liniara peste 5h, cu plateau peste 8.5h
        if hours < 5.0:
            base = 2
        elif hours < 7.0:
            base = 3 + (hours - 5.0) * 2.5    # de la 3 la 8
        elif hours <= 8.5:
            base = 8 + (hours - 7.0) * 0.7    # de la 8 la 9
        else:
            base = 9 - (hours - 8.5) * 0.5    # usor in jos peste 8.5h

        if self._is_burnout(day_idx):
            base -= 1.5
        # Zgomot
        q = int(round(base + self.rng.gauss(0, 0.8)))
        return max(1, min(10, q))

    def compute_energy(self, day_idx: int, dow: int, sleep_h: float, sleep_q: int) -> float:
        """
        Energia zilei = combinatie ponderata din:
          - Calitatea somnului (factor principal — corelatie demonstrata)
          - Ore dormite (factor secundar)
          - Momentum din ziua precedenta
          - Bias-ul zilei saptamanii
          - Trend pe termen lung
          - Burnout penalty
          - Zgomot natural
        """
        sleep_factor = (sleep_q / 10.0) * 0.6 + (min(sleep_h, 9.0) / 9.0) * 0.4
        # Pondere principala — somnul conteaza mai mult (corelatie crescuta)
        energy = 0.55 * sleep_factor
        # Momentum: 30% din energia de ieri (creste persistenta)
        energy += 0.30 * self.prev_energy
        # Ritm saptamanal: 15%
        energy += 0.15 * self.WEEKDAY_BIAS[dow]
        # Trend pe termen lung: pana la +5%
        energy += self._long_term_trend(day_idx)
        # Burnout: -25% (mai pronuntat)
        if self._is_burnout(day_idx):
            energy -= 0.25
        # Zgomot natural redus (zile anomalie)
        energy += self.rng.gauss(0, 0.05)
        # Bound
        energy = max(0.05, min(1.0, energy))
        self.prev_energy = energy
        return energy

    def num_tasks(self, energy: float, dow: int) -> int:
        """Numar de sarcini in functie de energie + bias zi (zgomot redus)."""
        expected = energy * 6 * self.WEEKDAY_BIAS[dow]
        n = int(round(self.rng.gauss(expected, 0.8)))
        return max(0, min(10, n))

    def num_pomos(self, energy: float, dow: int) -> int:
        """Numar de sesiuni Pomodoro (zgomot redus)."""
        expected = energy * 5 * self.WEEKDAY_BIAS[dow]
        n = int(round(self.rng.gauss(expected, 0.7)))
        return max(0, min(8, n))

    def pomo_duration_choice(self) -> int:
        """Alege durata pentru o sesiune pe baza preferintei personale."""
        durations = list(self.POMO_FREQUENCY.keys())
        weights = list(self.POMO_FREQUENCY.values())
        return self.rng.choices(durations, weights=weights)[0]

    def pomo_completed(self, duration: int, energy: float) -> bool:
        """Probabilitatea de finalizare scade cu durata si creste cu energia."""
        base = self.POMO_BASE_COMPLETION[duration]
        # Modulam cu energia: max 1.2x la energie 1.0, min 0.5x la energie 0.05
        modifier = 0.5 + 0.7 * energy
        prob = min(0.97, base * modifier)
        return self.rng.random() < prob

    def habit_completion_rate(self, energy: float, dow: int) -> float:
        """Rata de bifare a obiceiurilor — coreleaza puternic cu energia."""
        base = 0.40 + 0.55 * energy
        # Weekend, oamenii sunt mai relaxati cu obiceiurile
        if dow >= 5:
            base *= 0.80
        return min(0.98, max(0.10, base))

    def task_completion_hour(self, energy: float) -> int:
        """Ora de finalizare a unei sarcini — utilizator dimineata vs seara."""
        # Persoana mai matinal cand are energie mare, seara cand are energie mica
        if energy > 0.65 and self.rng.random() < 0.6:
            # Dimineata 9-12
            return self.rng.choices([9, 10, 11], weights=[1, 2, 1])[0]
        elif energy < 0.45 and self.rng.random() < 0.6:
            # Noapte 20-23
            return self.rng.choices([20, 21, 22, 23], weights=[1, 2, 2, 1])[0]
        # Variat
        return self.rng.choices(
            [9, 10, 11, 14, 15, 19, 20, 21],
            weights=[2, 3, 2, 2, 2, 3, 3, 2]
        )[0]


# ════════════════════════════════════════════════════════════════════════════
# UTILITAR HTTP
# ════════════════════════════════════════════════════════════════════════════

def get(path):    return requests.get(BASE_URL + path, timeout=10)
def post(path, d): return requests.post(BASE_URL + path, json=d, headers=HEADERS, timeout=10)
def delete(path): return requests.delete(BASE_URL + path, timeout=10)


def dt_iso(d: date, hour: int, minute: int = 0) -> str:
    return datetime(d.year, d.month, d.day, hour, minute).isoformat()


def check_backend():
    try:
        requests.get(BASE_URL.replace("/api", ""), timeout=3)
    except Exception:
        print("Backend nu raspunde la localhost:8080. Porneste Spring Boot.")
        sys.exit(1)


# ════════════════════════════════════════════════════════════════════════════
# CLEAR
# ════════════════════════════════════════════════════════════════════════════

def clear_user_data(user_id):
    print("  Sterg datele existente...")
    for endpoint, key in [("tasks", "tasks"), ("habits", "habits"),
                          ("pomodoro", "pomos"), ("sleep", "sleep")]:
        try:
            r = get(f"/{endpoint}/user/{user_id}")
            if r.ok:
                items = r.json()
                for it in items:
                    delete(f"/{endpoint}/{it['id']}")
                print(f"     - {endpoint}: sterse {len(items)}")
        except Exception as e:
            print(f"     - {endpoint}: eroare {e}")


# ════════════════════════════════════════════════════════════════════════════
# SEED
# ════════════════════════════════════════════════════════════════════════════

HABIT_NAMES = [
    "Sport / miscare",
    "Citit 20 minute",
    "Meditatie",
    "Fara telefon inainte de somn",
    "Plimbare in aer liber",
]

TASK_TEMPLATES = [
    ("Rezolvat tema la {subject}", "CLASSIC"),
    ("Studiat capitolul {n} din {subject}", "CLASSIC"),
    ("Proiect {subject} - parte {n}", "CLASSIC"),
    ("Recapitulare {subject}", "QUICK"),
    ("Email profesor {subject}", "QUICK"),
    ("Planificat ziua", "QUICK"),
    ("Citit articol despre {subject}", "RADAR"),
    ("Brainstorming {subject}", "RADAR"),
    ("Revizuit obiective saptamanale", "RADAR"),
]
SUBJECTS = ["Matematica", "Programare", "Baze de date", "Retele",
            "Algoritmi", "Machine Learning", "Sisteme de operare", "Licenta"]


def seed_habits(user_id, rng):
    habits = []
    for name in HABIT_NAMES:
        r = post("/habits/add", {"userId": user_id, "name": name})
        if r.ok:
            habits.append(r.json())
    return habits


def seed_all(user_id, days, start_date, seed):
    persona = PersonaModel(seed=seed, total_days=days)
    rng = persona.rng

    print(f"  Initializare model persoana (seed={seed})")
    print(f"  Perioade burnout: {persona.burnout_periods}")

    print("  Creez habits...")
    habits = seed_habits(user_id, rng)
    print(f"     -> {len(habits)} habits")

    # Variabile de stare pentru recuperare-somn
    prev_was_short = False

    print("  Generez zilele...")
    tasks_total = 0
    pomos_total = 0
    sleep_total = 0
    habit_log_total = 0

    for day_idx in range(days):
        d = start_date + timedelta(days=day_idx)
        dow = d.weekday()

        # ─── SOMNUL (noaptea precedenta) ──────────────────────────────
        hours = persona.sleep_hours(day_idx, dow, prev_was_short)
        prev_was_short = (hours < 6.0)
        quality = persona.sleep_quality(hours, day_idx)

        # Bedtime / wake — calcul realist
        if hours >= 7:
            bed_h = rng.choices([22, 23, 0], weights=[30, 50, 20])[0]
        else:
            bed_h = rng.choices([0, 1, 2], weights=[40, 40, 20])[0]
        bed_m = rng.randint(0, 59)
        bed_date_obj = d - timedelta(days=1) if bed_h >= 20 else d
        wake_total_min = bed_h * 60 + bed_m + int(hours * 60)
        wake_h = (wake_total_min // 60) % 24
        wake_m = wake_total_min % 60

        try:
            r = post("/sleep/add", {
                "userId": user_id,
                "bedtime": dt_iso(bed_date_obj, bed_h, bed_m),
                "wakeUpTime": dt_iso(d, wake_h, wake_m),
                "qualityScore": quality,
                "logDate": d.isoformat(),
            })
            if r.ok:
                sleep_total += 1
        except Exception:
            pass

        # ─── ENERGIA ZILEI ────────────────────────────────────────────
        energy = persona.compute_energy(day_idx, dow, hours, quality)

        # ─── TASKS (in functie de energie) ────────────────────────────
        n_tasks = persona.num_tasks(energy, dow)
        for _ in range(n_tasks):
            tpl, typ = rng.choice(TASK_TEMPLATES)
            title = tpl.format(
                subject=rng.choice(SUBJECTS),
                n=rng.randint(2, 9),
            )
            hour = persona.task_completion_hour(energy)
            minute = rng.randint(0, 59)
            try:
                r = post("/tasks/add", {
                    "userId": user_id,
                    "title": title,
                    "type": typ,
                    "status": "DONE",
                    "completedAt": dt_iso(d, hour, minute),
                    "xPosition": rng.uniform(15, 85),
                    "yPosition": rng.uniform(15, 85),
                })
                if r.ok:
                    tasks_total += 1
            except Exception:
                pass

        # ─── POMODORO (in functie de energie) ─────────────────────────
        n_pomos = persona.num_pomos(energy, dow)
        for _ in range(n_pomos):
            dur = persona.pomo_duration_choice()
            completed = persona.pomo_completed(dur, energy)
            hour = persona.task_completion_hour(energy)
            minute = rng.randint(0, 55)
            try:
                r = post("/pomodoro/add", {
                    "userId": user_id,
                    "durationMinutes": dur,
                    "wasCompleted": completed,
                    "startTime": dt_iso(d, hour, minute),
                })
                if r.ok:
                    pomos_total += 1
            except Exception:
                pass

        # ─── HABITS (in functie de energie) ───────────────────────────
        habit_rate = persona.habit_completion_rate(energy, dow)
        for habit in habits:
            if rng.random() < habit_rate:
                try:
                    r = post(f"/habits/{habit['id']}/log",
                             {"date": d.isoformat()})
                    if r.ok:
                        habit_log_total += 1
                except Exception:
                    pass

        # Progress indicator
        if (day_idx + 1) % 30 == 0:
            print(f"     ... ziua {day_idx + 1}/{days} (energie azi: {energy:.2f})")

    print(f"\n  Total generat:")
    print(f"     - {tasks_total} tasks")
    print(f"     - {pomos_total} sesiuni Pomodoro")
    print(f"     - {sleep_total} inregistrari de somn")
    print(f"     - {habit_log_total} bifari de obiceiuri")


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Seed data v2 (cu tipare realiste) pentru ProductivityApp"
    )
    parser.add_argument("--user",  type=int, default=2, help="User ID")
    parser.add_argument("--days",  type=int, default=365, help="Cate zile sa generez")
    parser.add_argument("--seed",  type=int, default=42, help="Seed random pentru reproducibilitate")
    parser.add_argument("--clear", action="store_true", help="Sterge datele existente intai")
    args = parser.parse_args()

    print(f"\n{'=' * 65}")
    print(f"  SEED DATA v2 — User {args.user} · {args.days} zile · seed={args.seed}")
    print(f"{'=' * 65}")

    check_backend()

    if args.clear:
        clear_user_data(args.user)

    start_date = date.today() - timedelta(days=args.days)
    print(f"  Perioada: {start_date} -> {date.today()}\n")

    seed_all(args.user, args.days, start_date, args.seed)

    print(f"\n{'=' * 65}")
    print(f"  Gata! Pentru antrenare:")
    print(f"     python ml_engine.py --user {args.user} --train")
    print(f"{'=' * 65}\n")


if __name__ == "__main__":
    main()
