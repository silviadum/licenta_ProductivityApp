# FocusFlow

A mobile productivity app that combines task management, focus sessions, habit tracking, and sleep monitoring into a single platform. It uses machine learning to predict your daily productivity and gives recommendations based on your own data.

Built as my bachelor's thesis project at University Politehnica of Bucharest, 2026.

## What it does

Most productivity apps focus on one thing: tasks, or Pomodoro, or habits, or sleep. FocusFlow tracks all four together and uses the combined data to:

- Calculate a daily productivity score
- Predict if today is going to be a good, normal, or weak day
- Suggest your most productive hours of the day
- Find your best and worst weekday
- Detect the Pomodoro duration that works best for you
- Show the relationship between sleep and next-day productivity
- Track streaks and overall trends

All recommendations are shown as plain text sentences, not just numbers on a chart.

## Tech stack

**Frontend**
- React Native + Expo (Android & iOS)
- JavaScript

**Backend**
- Java 21 + Spring Boot
- Spring Data JPA + Hibernate
- MySQL 8.0

**Machine Learning**
- Python 3.13
- scikit-learn, pandas, NumPy, SciPy
- Random Forest classifier on a 30-feature vector
- TimeSeriesSplit cross-validation

## Architecture

```
[ React Native app ] ──HTTP/JSON──> [ Spring Boot REST API ] ──JPA──> [ MySQL ]
                                              │
                                              └──ProcessBuilder──> [ Python ML script ]
```

The backend exposes a REST API. When the app asks for a prediction, the backend runs the Python ML script as a separate process and parses the result.

## ML pipeline

The model predicts a class (weak / normal / good) for the current day. It does not use today's data when making the prediction (`shift(1)` on all derived features) so there is no data leakage.

The 30 features cover six time horizons:

| Group | Count | What it captures |
|-------|-------|------------------|
| Immediate context | 12 | Last 1–7 days |
| Personal baseline | 4 | Today vs your average |
| Long-term direction | 3 | 30-day trend |
| Weekly patterns | 2 | How you usually do on this weekday |
| Volatility | 2 | How stable you are |
| Streak & momentum | 2 | Consecutive good/bad days |
| Interactions & seasonality | 5 | Cross-products and monthly cycles |

I compared three models: Logistic Regression (baseline), Random Forest, and XGBoost. Random Forest won with a cross-validated accuracy of 65.1% and AUC of 0.866, which is in the standard range for behavioral prediction.

## Productivity score formula

```
S = 4 × tasks_done
  + 30 × (habits_done / total_habits)
  + 5  × pomodoro_sessions
  + 8  × (focus_minutes / 60)
```

The weights were validated through sensitivity analysis: ±20% variation in any weight changes the classification of only ~1.6% of days. So the exact numbers are not critical — the relative ordering is what matters.

## Project structure

```
ProductivityApp/
├── backend/      Spring Boot REST API
├── frontend/     React Native app
└── ml/
    ├── ml_engine.py        Training + prediction
    ├── seed_data_v2.py     Synthetic data generator
    ├── main.py
    ├── requirements.txt
    └── models/             Trained model files (.pkl)
```

## Running locally

You need: Java 21, Node.js 18+, Python 3.10+, MySQL 8.

**Backend**
```bash
cd backend
./mvnw spring-boot:run
# Runs on http://localhost:8080
```

**Frontend**
```bash
cd frontend
npm install
npx expo start
# Scan the QR code with Expo Go
```

**ML — generate synthetic data and train the model**
```bash
cd ml
pip install -r requirements.txt

# Create a user first via the app, then:
python seed_data_v2.py --user 2 --clear
python ml_engine.py --user 2 --train
```

After training, the model is saved in `ml/models/user_2/` and predictions become available in the app.

## Data

The model was trained and evaluated on synthetic data because collecting 365 days of real user data was not possible during the thesis. The data generator simulates a realistic persona with:

- Sleep-productivity correlation
- Weekly rhythm (lower on Mondays, peak Tue–Wed, lower on weekends)
- Two burnout periods per year
- Random noise and roughly 5% anomalies

The model reaching 65% accuracy (not 95%) is a sign that the data has realistic complexity, not artificially clean patterns.

## Limitations

- Synthetic data only — no real users yet
- Recall on the "weak day" class is low because there are very few weak days in the test set (3 out of 73)
- ML inference runs through `ProcessBuilder`, which works locally but would need to be replaced with a microservice for production
- Authentication is basic (BCrypt password hashing only, no JWT)

## What's next

- Integration with smartwatches / Fitbit for automatic sleep tracking
- Sync with Google Calendar to schedule focus sessions in free slots
- Move the backend to the cloud and replace `ProcessBuilder` with a Python REST microservice
- Add JWT auth and stronger password policy

## License

MIT

## Author

Dumitrache Silvia-Georgiana
University Politehnica of Bucharest, Faculty of Automatic Control and Computers
Thesis advisor: Prof. dr. ing. Liliana Dobrica
2026
