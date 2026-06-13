# 🧠 Productivity Intelligence Engine — Setup & Run

Pipeline-ul de **Machine Learning** pentru aplicația Productivity AI.

---

## 📦 Componente

| Fișier | Descriere |
|---|---|
| `ml_engine.py` | Modul 1 (regresie) + Modul 2 (clustering). Antrenează și salvează modelele. |
| `seed_data.py` | Generează 60-365 zile de date test cu patternuri controlate. |
| `productivity_insights.py` | Analiză offline cu grafice matplotlib. |
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
🤖 Modul 1: Antrenare modele de regresie...
─────────────────────────────────────────────
📊 REZULTATE MODELE DE REGRESIE
─────────────────────────────────────────────
Model                       R²      MAE     RMSE       CV R² (μ±σ)
Ridge Regression         0.512    8.43    10.21    0.487 ± 0.043
Gradient Boosting        0.715    5.89     7.31    0.692 ± 0.041  ⭐
─────────────────────────────────────────────
🏆 Cel mai bun model: Gradient Boosting

🔬 Modul 2: Gruparea comportamentală (K-Means)...
   → k optim = 3 clustere (Silhouette = 0.412)
   → Profiluri:
      • Deep focus: scor=82, tasks=3.2, pomos=4.1, somn=7.8h
      • Întreținere: scor=51, tasks=1.5, pomos=2.0, somn=7.1h
      • Odihnă: scor=18, tasks=0.4, pomos=0.3, somn=8.5h

💾 Modele salvate în: D:/licenta/ProductivityApp/ml/models/user_4
📊 Generare rapoarte PNG...
   📄 user_4_regression.png
   📄 user_4_feature_importance.png
   📄 user_4_clustering.png
```

### 5. Testează predicția

```bash
python -X utf8 ml_engine.py --user 4 --predict
```

Output:
```
🔮 Predicție pentru User 4 — 2026-05-12:
   Scor estimat: 68.3/100 ↑
   Media ultimelor 7 zile: 61.2/100
   Model: Gradient Boosting (CV R² = 0.692)
   Antrenat pe: 287 zile
```

---

## 🔌 Integrare cu aplicația

După ce ai antrenat modelele:

- **Dashboard mobil** → vezi cardul **„Predicție ML · Mâine"** (mov)
- **Chat (sparkles icon)** → asistent rule-based instant pe datele tale reale
- **Pagina Progres** → toate insights-urile statistice (corelație Pearson, heatmap, etc.)

---

## 📊 Pentru lucrarea de licență

După `--train`, în folderul `reports/` vei avea 3 PNG-uri perfect de pus în capitolul 4.3:

1. **`user_X_regression.png`** — comparație R², MAE, predicție vs. realitate
2. **`user_X_feature_importance.png`** — ce caracteristici contează pentru tine (din Gradient Boosting)
3. **`user_X_clustering.png`** — Elbow + Silhouette + vizualizare PCA 2D

---

## 🧠 Algoritmii folosiți (sinteză pentru lucrare)

### Modul 1 — Regresie supervizată
- **Ridge Regression** — baseline liniar cu regularizare L2
- **Gradient Boosting** — ensemble de arbori construit iterativ, gold standard pentru date tabelare
- **Feature engineering**: lag features (3 zile), rolling mean (3 și 7 zile), codificare ciclică sin/cos a zilei săptămânii
- **Validare**: train/test split 80/20 + k-fold cross-validation (k=5)
- **Metrici**: R², MAE, RMSE

### Modul 2 — Clustering nesupervizat
- **K-Means** cu numărul optim de clustere determinat prin:
  - **Metoda Elbow** (curba WCSS)
  - **Scorul Silhouette** (cohesiune + separare)
- **PCA** (Principal Component Analysis) pentru reducerea dimensionalității la 2D și vizualizare
- **Profilarea clusterelor**: zile de focus / întreținere / odihnă

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
