# 🧠 Productivity Intelligence Engine — Setup & Run

Pipeline-ul de **Machine Learning** (clasificare 3-clase) pentru aplicația Productivity AI.

---

## 📦 Componente

| Fișier | Descriere |
|---|---|
| `ml_engine.py` | Pipeline ML: antrenare clasificator + predicție live. |
| `seed_data.py` | Generează 60-365 zile de date test cu patternuri controlate. |
| `productivity_insights.py` | Analiză descriptivă cu grafice matplotlib (opțional, pentru lucrare). |
| `models/user_X/` | Modele antrenate (joblib .pkl) + metadata. |
| `reports/` | Grafice PNG pentru lucrarea de licență. |

---

## 🚀 Setup pas cu pas

### 1. Instalează dependențele Python

```bash
cd D:/licenta/ProductivityApp/ml
pip install -r requirements.txt
```

### 2. Pornește backend-ul Spring + MySQL

Folosește IDE-ul tău (IntelliJ, VSCode) sau:
```bash
cd backend && mvn spring-boot:run
```

### 3. Generează datele de seed (365 zile, recomandat pentru ML)

```bash
cd ml
python -X utf8 seed_data.py --user 4 --days 365 --clear
```

### 4. Antrenează modelele ML

```bash
python -X utf8 ml_engine.py --user 4 --train
```

Output așteptat:
```
🤖 Antrenare modele de clasificare...
─────────────────────────────────────────────────────────────
📊 REZULTATE MODELE DE CLASIFICARE (3 clase: SLABA / NORMALA / BUNA)
─────────────────────────────────────────────────────────────
Model                          Acc    Prec   Rec    F1    AUC    CV Acc
Logistic Regression          0.576  0.562  0.576  0.565  0.717  0.548 ⭐
Random Forest Classifier     0.485  0.464  0.485  0.470  0.645  0.506
─────────────────────────────────────────────────────────────
🏆 Cel mai bun model: Logistic Regression

Confusion Matrix (Logistic Regression):
            Pred:  SLABA  NORMALA  BUNA
Real    SLABA:      8       4       3
Real  NORMALA:      5       8       9
Real     BUNA:      2       5      22

💾 Modele salvate in: ml/models/user_4
📊 Generare rapoarte PNG...
   📄 user_4_classification.png
   📄 user_4_roc_curves.png
```

### 5. Testează predicția

```bash
python -X utf8 ml_engine.py --user 4 --predict
```

Output:
```
🔮 Predicție AZI pentru User 4 — 2026-06-13:
   Clasa estimată: Buna (BUNA)
   Încrederea: 64.7%
   Probabilități:
      • SLABA: 4.0%
      • NORMALA: 31.3%
      • BUNA: 64.7%
   Model: Random Forest Classifier (CV Accuracy = 0.498)
   Antrenat pe: 365 zile
```

---

## 🔌 Integrare cu aplicația

După ce ai antrenat modelele:

- **Dashboard mobil** → vezi cardul **„Prognoză"** care afișează un mesaj natural pe baza clasei prezise
- **Pagina Progres** → toate insights-urile statistice (corelație Pearson, heatmap, recomandări, etc.) calculate live de backend

---

## 📊 Pentru lucrarea de licență

După `--train`, în folderul `reports/` vei avea 2 PNG-uri pentru capitolul 4.3:

1. **`user_X_classification.png`** — 4 subploturi: comparație metrici (accuracy, precision, recall, F1), CV stability, **confusion matrix**, distribuție clase
2. **`user_X_roc_curves.png`** — curbe ROC (one-vs-rest) pentru fiecare clasă × fiecare model

---

## 🧠 Algoritmii folosiți (sinteză pentru lucrare)

### Clasificare 3-clase
- **Țintă:** ziua DE AZI e SLABĂ (scor < 40) / NORMALĂ (40-70) / BUNĂ (> 70)
- **Logistic Regression** — clasificator liniar cu regularizare L2, baseline
- **Random Forest Classifier** — ensemble de arbori cu class_weight balanced
- **Feature engineering**: 12 caracteristici — lag features (scoruri din ultimele 3 zile), rolling mean (3 și 7 zile, fără azi), codificare ciclică sin/cos a zilei săptămânii (azi), ore + calitate somn (azi-noapte), activitatea din ZIUA PRECEDENTĂ (taskuri, Pomodoros, rata obiceiurilor)
- **Validare**: train/test split temporal 80/20 + k-fold cross-validation (k=5)
- **Metrici**: accuracy, precision, recall, F1-score, ROC-AUC (one-vs-rest weighted), confusion matrix

---

## 🆘 Troubleshooting

**„Nu mă pot conecta la backend"** → Pornește Spring Boot (`mvn spring-boot:run`)

**„Date insuficiente pentru ML"** → Re-rulează seed cu mai multe zile: `--days 365`

**Erorile cu encoding UTF-8 pe Windows** → Adaugă mereu `-X utf8` la `python`

---

## 🎯 Flux complet pentru demo

```bash
# 1. Pornește MySQL + Spring (în 2 terminale)
# 2. Seed
python -X utf8 seed_data.py --user 4 --days 365 --clear

# 3. Antrenare
python -X utf8 ml_engine.py --user 4 --train

# 4. Predicție
python -X utf8 ml_engine.py --user 4 --predict

# 5. Pornește Expo și verifică în mobil
cd ../frontend && npx expo start -c
```
