# 📱 PRODUCTIVITY AI — Descriere completă a aplicației

> Aplicație inteligentă de productivitate pentru lucrarea de licență
> Departamentul Automatică și Informatică Industrială, Facultatea de Automatică și Calculatoare, UNSTPB
> An: 2026

---

## 1. CE FACE APLICAȚIA

Productivity AI este o aplicație mobilă (Android + iOS) care **ajută utilizatorii să-și gestioneze timpul, sarcinile, obiceiurile și somnul, oferindu-le în plus o analiză personalizată a comportamentului lor pentru a-i ajuta să devină mai productivi**.

Spre deosebire de aplicațiile clasice de pe piață (care fac un singur lucru bine — fie taskuri, fie focus, fie habits, fie somn), Productivity AI integrează **toate aceste patru zone într-o singură platformă** și aplică pe datele colectate **algoritmi de machine learning antrenați** (Gradient Boosting și Ridge Regression) împreună cu **analiză statistică** (corelație Pearson), care identifică tipare individuale și generează **predicții și recomandări personalizate**, prezentate utilizatorului în limbaj natural.

### 1.1. Funcționalități principale

#### A. Autentificare și onboarding
- Înregistrare cu email, username, parolă (validare în timp real: format email cu regex, parolă min. 5 caractere, indicator vizual de tărie a parolei)
- Login cu opțiunea „Ține-mă logat" (persistare în AsyncStorage → auto-login la repornire)
- Ecran de onboarding cu 3 sliduri la prima utilizare (explică funcționalitățile)
- Logout cu confirmare cross-platform

#### B. Managementul sarcinilor (Tasks)
- **3 tipuri de taskuri**:
  - `CLASSIC` — taskuri obișnuite („Rezolvat tema la matematică")
  - `QUICK` — taskuri de maxim 15 minute („Planificat ziua")
  - `RADAR` — taskuri „uitate" / fără termen, afișate distinct
- **Drag & drop** pentru reordonare (long press + drag)
- **Swipe actions** pe taskuri:
  - Swipe stânga → marchează ca finalizat
  - Swipe dreapta → șterge (cu confirmare)
- Adăugare rapidă din câmpul de input

#### C. Pomodoro Timer
- Durate configurabile (15 / 25 / 45 / 60 minute)
- Marchează sesiunile ca finalizate sau abandonate
- Salvare durată reală + oră de start pentru analiză

#### D. Habit Tracker (Obiceiuri)
- Adăugare / ștergere obiceiuri active
- Vedere săptămânală cu 7 cercuri pe rând (un cerc / zi)
- Bifare cu un tap pe ziua corespunzătoare
- Calcul automat al ratei zilnice de completare

#### E. Sleep Tracker (Somn)
- Logare oră culcare + oră trezire
- Calitate subiectivă a somnului (1-10)
- Calcul automat al duratei somnului
- Istoric vizual cu durata pe noapte

#### F. Pagina Progres (Insights personalizate)
- **Card recomandări** (galben) — 5-9 sfaturi personalizate generate din datele utilizatorului
- **Card trend** — direcția generală a productivității (creștere / scădere / stabil), în text natural
- **Card-uri de descoperiri**:
  - Cea mai productivă zi a săptămânii
  - Cea mai relaxată zi a săptămânii
  - Durata Pomodoro care îți merge cel mai bine
  - Compararea sesiunilor scurte vs. lungi
  - Cât somn îți aduce zilele cele mai bune
  - Cum îți afectează somnul ziua următoare (legătură pozitivă / negativă, text natural)
- **Grafice native**:
  - Linie cu evoluția în timp (zilnic + tendință generală)
  - Bare pentru activitate per oră (0-23)
  - Heatmap zi × interval orar (7×4)
  - Bare cu scor mediu pe zi a săptămânii
  - Bare cu Pomodoro per durată
  - Bare cu ore somn → scor a doua zi
  - Bare cu calitate somn → productivitate

#### G. Dashboard (ecranul principal)
- Salut contextual cu iconiță (☀️ dimineața, 🌤️ ziua, 🌙 seara, 🌚 noaptea)
- Chip cu **streak** (zile consecutive cu activitate, format „60 🔥 zile streak")
- Chip cu **interval productiv** dacă e activat
- **Card „Sfatul zilei"** — text rotativ din recomandările sistemului, schimbă în fiecare zi
- **Card „Prognoză" (ALIMENTAT DE MODELUL ML LIVE)** — la fiecare deschidere de dashboard, modelul de Gradient Boosting antrenat face inferință și predicția este transformată într-un mesaj natural (5 niveluri: „O zi de top", „O zi bună pentru focus", „O zi obișnuită", „O zi mai lentă", „O zi pentru recuperare"). Cardul dispare elegant dacă modelul nu a fost încă antrenat.
- **Radar circular** cu 3 cercuri navigabile (TASKS / POMODORO / HABITS), fiecare cu contorul de azi
- Animație de puls subtilă pe inelul radarului
- 3 quick actions: „Task nou", „Pomodoro", „Loghează somn"
- Pull-to-refresh pentru reîncărcarea datelor

#### H. Profil
- Avatar cu inițialele utilizatorului
- Editare profil (username + parolă cu input de tip parolă cu toggle ochi)
- **Grilă de insigne (achievements)** — 12 niveluri:
  - Primul pas, Constant (10 tasks), Forță (50 tasks), Focus on, Concentrat, Trei la rând, Săptămâna perfectă, Disciplină de fier (30 zile streak), Habit pornit, Bun-dormitor, O oră de focus, Maraton (8h focus)
  - Fiecare cu progres procentual + iconiță colorată când e câștigată
- **Secțiunea ASPECT** — toggle Dark / Light theme (persistat în AsyncStorage)
- **Secțiunea NOTIFICĂRI** — 3 tipuri:
  - Reminder habits zilnic
  - Reminder de culcare
  - Motivație de dimineață
  - Fiecare configurabilă cu propriul interval HH:MM
- **Secțiunea PREFERINȚE** — durată default Pomodoro (15/25/45/60 min), săptămâna începe Luni/Duminică
- **Secțiunea INTERVAL PRODUCTIV** — utilizatorul își setează fereastra orară în care dorește să fie activ (ex: 16:00–22:00 pentru student cu cursuri 8-16); aplicația își ajustează semnalele în acest interval
- **Versiunea aplicației** (1.0.0)
- Buton de deconectare

### 1.2. Componenta de inteligență

Aplicația include un **sistem de inteligență pe două straturi**:

#### Strat A — Machine Learning live (rulează în aplicație)
- **Modele antrenate** pe istoricul utilizatorului folosind scikit-learn:
  - **Ridge Regression** (baseline liniar cu regularizare L2)
  - **Gradient Boosting** (ensemble nonlinear)
- **Selecția modelului** se face automat prin **k-fold cross-validation** (k=5) — modelul cu cel mai bun R² mediu e ales pentru predicție
- **Predicția live**: la fiecare deschidere a dashboard-ului, backend-ul Spring apelează scriptul Python (`ml_engine.py --predict`), care încarcă modelul antrenat (`.pkl`) și face inferență pentru ziua următoare
- **Rezultatul predicției** (scor numeric) este transformat de utilitar `forecast.js` într-un mesaj natural în limba română, fără cifre vizibile pentru utilizator
- **Modele antrenate suplimentar** (rulate offline pentru lucrare):
  - **K-Means clustering** cu Elbow method + Silhouette score pentru numărul optim de clustere
  - **PCA** (Principal Component Analysis) pentru vizualizare 2D
  - **Profilarea automată a clusterelor** (zile de focus / întreținere / odihnă)

#### Strat B — Analiză statistică + recomandări (în backend live)

Pe lângă modelul ML, backend-ul calculează direct, pentru fiecare cerere:

1. **Scoring multidimensional ponderat al productivității zilnice**
   - Formulă: `S_brut = 4·tasks + 30·(habits/total_habits) + 5·pomos + 8·(minute_focus/60)`
   - Normalizare pe intervalul [0, 100]: `S = S_brut / max(S_brut) × 100`

2. **Corelație Pearson** între ore de somn / calitate somn și productivitatea din ziua următoare
   - Rezultatul (-1 la +1) este transformat în text natural pentru utilizator
   - Nu se afișează cifre raw în UI

3. **Detecția intervalelor optime** (Dimineață / După-amiază / Seară / Noapte) prin agregare ponderată

4. **Detecția zilei optime și a celei cu cel mai mic scor** prin grupare pe ziua săptămânii

5. **Heatmap zi × interval** (7 zile × 4 intervale) pentru identificarea ferestrelor temporale productive

6. **Rolling average** pe 7 zile pentru netezirea graficului de evoluție

7. **Detecția trendului** (creștere / scădere / stabil) prin compararea primei jumătăți a perioadei cu a doua

8. **Streak** — zile consecutive cu activitate, calculat de la data curentă înapoi

9. **Sistem de recomandări bazat pe reguli** — generează automat 5-9 sfaturi personalizate în limba română, în funcție de tiparele detectate (ex: „Sesiunile scurte îți merg mai bine: 87% vs 52%. Setează durata default în profil.")

---

## 2. CE TEHNOLOGII FOLOSEȘTE ȘI DE CE

### 2.1. Backend

| Tehnologie | Versiune | De ce |
|---|---|---|
| **Java** | 21 (LTS) | Limbaj robust, tipizat static, performant. Versiunea 21 = LTS, suportată oficial. |
| **Spring Boot** | 3.2.4 | Cel mai folosit framework Java pentru API REST. Auto-configurare, ecosistem matur, productiv. |
| **Spring Data JPA** | (inclus) | Mapare automată obiecte → tabele, repository pattern, query-uri generate din nume metodă. |
| **Hibernate** | (inclus prin JPA) | Implementare ORM standard. |
| **MySQL Connector/J** | (latest) | Driver oficial pentru conectarea la MySQL. |
| **MySQL** | 8.0 | Bază de date relațională robustă, populară, gratuită, suport pentru tipuri moderne. |
| **Spring Security Crypto** | (separat de full security) | Folosit doar pentru `BCryptPasswordEncoder` — hash parole. Fără filter chain (rute deschise, simplitate). |
| **Maven** | (build tool) | Manager de dependențe + build standard pentru Java. |
| **Jackson** | (inclus) | Serializare JSON automată pentru REST. |
| **Java ProcessBuilder** | (JDK standard) | Folosit de `MLPredictionController` pentru a apela scriptul Python `ml_engine.py --predict` la fiecare cerere de predicție, citind output-ul prin stream UTF-8. |

**De ce Spring Boot și nu Node.js/Python pentru backend?** Tematica licenței la Automatică este orientată pe sisteme enterprise robuste — Spring Boot e standardul în industrie pentru Java backends, iar Java 21 este un limbaj puternic, tipizat, ușor de apărat la comisie.

### 2.2. Frontend mobil

| Tehnologie | Versiune | De ce |
|---|---|---|
| **React Native** | 0.81.5 | Framework cross-platform — un singur cod sursă pentru iOS + Android. |
| **Expo SDK** | 54 | Platformă peste React Native — facilități native (notificări, file system, gesture handling) fără configurare nativă manuală. |
| **Expo Router** | v6 | Routing bazat pe structura fișierelor (file-based), similar cu Next.js. |
| **React** | 19.1.0 | Biblioteca UI. |
| **AsyncStorage** | 2.2.0 | Persistare locală key-value (setări, theme, „remember me", flag onboarded). |
| **axios** | 1.14.0 | Client HTTP cu interceptors și auto-detect IP pentru hot-reload. |
| **expo-notifications** | 0.32.17 | Notificări locale programate (reminder habits / culcare / motivație). |
| **expo-haptics** | 15.0.8 | Feedback haptic pe interacțiuni. |
| **react-native-gesture-handler** | 2.28.0 | Bază pentru swipe + drag & drop. |
| **react-native-reanimated** | 4.1.1 | Animații performante (puls radar, transitions). |
| **react-native-draggable-flatlist** | (latest) | Listă cu drag & drop nativ pentru reordonare taskuri. |
| **react-native-safe-area-context** | 5.6.0 | Gestiunea corectă a notch-ului / home indicator pe iPhone X+. |
| **@expo/vector-icons** | 15.0.3 | Set de iconițe (Ionicons folosit). |

**De ce React Native și nu Flutter/native?**
- Familiaritate cu JavaScript/React (curbă de învățare mai mică)
- Hot reload + Expo = ciclu de dezvoltare extrem de rapid
- Cross-platform fără sacrificii majore de performanță
- Comunitate uriașă + ecosistem matur

### 2.3. Machine Learning / Analiză

| Bibliotecă | De ce |
|---|---|
| **scikit-learn** | Bibliotecă standard pentru ML în Python — Ridge, Gradient Boosting, K-Means, PCA, metrics, cross-validation. |
| **pandas** | Manipularea DataFrame-urilor cu date temporale. |
| **NumPy** | Calcul numeric vectorizat. |
| **SciPy** | `scipy.stats.pearsonr` pentru corelația Pearson cu p-value. |
| **matplotlib** | Generarea graficelor PNG pentru lucrarea scrisă. |
| **joblib** | Serializarea modelelor antrenate (alternativă la pickle, optimizată pentru obiecte NumPy). **Folosit de aplicație** pentru a încărca modelele `.pkl` la fiecare predicție live. |
| **requests** | Apeluri HTTP către backend-ul Spring pentru încărcarea datelor utilizatorului. |

**De ce Python pentru ML și nu Java?** Python are ecosistemul de ML cel mai matur și standardizat (scikit-learn, pandas). În Java există alternative (Weka, DL4J), dar sunt mai puțin populare și mai dificil de explicat la comisie.

**De ce Ridge + Gradient Boosting și nu doar unul?**
- **Ridge Regression** = baseline liniar cu regularizare L2 (evită overfitting); demonstrează că studentul a comparat cu un model simplu
- **Gradient Boosting** = model nonlinear de tip ensemble; de obicei câștigă, demonstrează că se cunosc tehnici moderne
- Modelele se compară prin **k-fold cross-validation** și se alege automat cel cu cel mai bun R² mediu; acesta este modelul care va rula live în aplicație
- **Random Forest** ar fi fost redundant cu GB (ambele sunt ensemble-uri de arbori) — a fost eliminat pentru simplitate

### 2.4. Bază de date

**MySQL 8** cu schema generată automat de Hibernate (`ddl-auto=update`). Tabele:
- `users` (id, username, email, password — hash BCrypt)
- `tasks` (id, user_id, title, type, status, due_date, completed_at, x_position, y_position, sort_order, project_id)
- `habits` (id, user_id, name, is_active)
- `habit_logs` (id, habit_id, date_completed)
- `pomodoro_sessions` (id, user_id, task_id, duration_minutes, was_completed, start_time)
- `sleep_logs` (id, user_id, log_date, bedtime, wake_up_time, quality_score)
- `projects` (id, name, user_id) — folosit minimal

### 2.5. Securitate

- **BCrypt** cu cost factor 10 pentru hash-ul parolelor
- **Migration automată** pentru parolele plaintext legacy (la primul login reușit, parola se re-hash-uiește)
- **Validări frontend** (regex email, lungime parolă) ca primă linie de protecție UX
- CORS deschis cu `@CrossOrigin(origins = "*")` — acceptabil pentru aplicație în dezvoltare, dar de restrâns în producție

---

## 3. CE NU FOLOSEȘTE ȘI DE CE (decizii informate)

- **Fără LLM (Llama, GPT, Gemini)**: am evaluat integrarea unui model lingvistic mare local prin Ollama cu arhitectură RAG, dar am ales să rămân pe analiză statistică și ML clasic pentru a păstra controlul total al răspunsurilor și pentru a evita complexitatea de setup la demo. Asistentul conversațional este în versiunea actuală bazat pe reguli (rule-based) — rapid, predictibil, fără dependențe externe.
- **Fără Random Forest**: redundant cu Gradient Boosting; eliminarea simplifică pipeline-ul și prezentarea fără pierdere de performanță.
- **Fără Spring Security filter chain**: rutele nu necesită autentificare per-endpoint (toate datele se filtrează prin `userId` din request); s-a folosit doar `spring-security-crypto` pentru BCrypt.
- **Fără microservicii**: backend monolit Spring Boot — sub-scale total justificat pentru o aplicație single-user demonstrativă.
- **Fără Redis sau cache**: volumul de date e mic și API-urile sunt rapide.
- **Fără WebSocket / push în timp real**: nu există funcții care să necesite update live.
- **Fără cloud deployment**: rulare locală (MySQL + Spring pe PC, Expo pe telefon prin LAN); justificabil pentru un proiect demonstrativ.

---

## 4. ARHITECTURA SISTEMULUI

### 4.1. Arhitectura pe trei straturi + bridge ML

```
┌─────────────────────────────────────────┐
│  FRONTEND (React Native + Expo)         │
│  - UI Dashboard / Tasks / Habits / etc. │
│  - State local cu React hooks           │
│  - axios pentru HTTP                    │
│  - AsyncStorage pentru persistare       │
│  - forecast.js: scor ML → text natural  │
└──────────────────┬──────────────────────┘
                   │  HTTP REST (JSON)
                   ▼
┌─────────────────────────────────────────┐
│  BACKEND (Spring Boot + Java 21)        │
│  - Controllers REST (@RestController)   │
│  - MLInsightsController: statistici     │
│  - MLPredictionController: bridge ML    │
│       ↓ ProcessBuilder                  │
│       └─→ ml_engine.py --predict        │
│             ↓ joblib.load               │
│             └─→ regression.pkl (model)  │
│  - JPA repositories                     │
│  - BCrypt password hashing              │
└──────────────────┬──────────────────────┘
                   │  JDBC
                   ▼
┌─────────────────────────────────────────┐
│  BAZA DE DATE (MySQL 8)                 │
│  - Schema auto-managed prin Hibernate   │
│  - 7 tabele relaționale                 │
└─────────────────────────────────────────┘

         ┌── separat — antrenare ───────┐
         │  PYTHON ML (offline + bridge)│
         │  - seed_data.py (testing)    │
         │  - ml_engine.py:             │
         │     • --train (offline)      │
         │       → salvează .pkl        │
         │     • --predict (LIVE)       │
         │       chemat de backend      │
         │  - productivity_insights.py  │
         │  - Generează grafice PNG     │
         └──────────────────────────────┘
```

### 4.2. Fluxul tipic al unei cereri

Exemplu 1 — utilizatorul deschide pagina **Progres**:

1. **Frontend** (`progres.js`) apelează `MLService.getInsights(userId)`
2. **axios** trimite `GET http://192.168.x.x:8080/api/ml/insights/{userId}`
3. **Spring** routează către `MLInsightsController.insights(userId)`
4. Controller-ul folosește repository-urile JPA pentru a încărca: sarcini, obiceiuri + logurile, sesiuni Pomodoro, somn
5. Aplică **algoritmii statistici**:
   - Calculează scorul brut pentru fiecare zi activă + normalizează 0-100
   - Grupează pe ziua săptămânii, interval orar, durată Pomodoro, ore somn
   - Calculează corelația Pearson somn ↔ productivitate
   - Construiește heatmap-ul 7×4
   - Calculează streak-ul
   - Generează recomandările bazate pe reguli (5-9 sfaturi)
6. Returnează un **JSON unic** cu toate datele
7. Frontend-ul randează 7 chart-uri native + card-uri text natural

Exemplu 2 — utilizatorul deschide **Dashboard-ul** (flux ML live):

1. **Frontend** (`dashboard.js`) apelează în paralel mai multe endpoint-uri, printre care `MLService.predict(userId)`
2. **axios** trimite `GET http://192.168.x.x:8080/api/ml/predict/{userId}`
3. **Spring** routează către `MLPredictionController.predict(userId)`
4. Controller-ul:
   - Verifică dacă există modelul antrenat (`models/user_X/regression.pkl`)
   - Dacă da, lansează un **ProcessBuilder** care apelează `python ml_engine.py --user X --predict`
5. **Python**:
   - Încarcă modelul `.pkl` cu `joblib.load`
   - Construiește vectorul de caracteristici (lag features, rolling mean, cyclical encoding, ore somn, etc.) pentru ziua curentă
   - Face inferență cu modelul de Gradient Boosting (sau Ridge, după selecția prin CV)
   - Afișează la stdout scorul prezis + media recentă
6. **Spring** parsează output-ul și returnează JSON: `{ available: true, predicted_score, recent_avg, delta }`
7. **Frontend** (`forecast.js`) transformă `delta` într-un mesaj natural în limba română prin 5 praguri (de la „O zi de top" la „O zi pentru recuperare") și afișează cardul pe dashboard cu iconiță, titlu și text — **fără cifre vizibile**

### 4.3. Detecția automată a IP-ului pentru testare pe telefon real

Fișierul `services/api.js` detectează automat baseURL în funcție de mediu:
- Pe web → `http://localhost:8080`
- Pe Expo Go pe telefon → ia IP-ul calculatorului din `Constants.expoConfig.hostUri` și construiește `http://192.168.x.x:8080`

Astfel aplicația merge fără modificări manuale când se schimbă rețeaua.

---

## 5. STRUCTURA DE FIȘIERE

```
D:/licenta/ProductivityApp/
│
├── backend/
│   ├── pom.xml
│   └── src/main/
│       ├── java/com/licenta/
│       │   ├── App.java                            (entry point Spring)
│       │   ├── config/
│       │   │   └── PasswordConfig.java             (BCrypt bean)
│       │   ├── controller/
│       │   │   ├── UserController.java             (register, login, update)
│       │   │   ├── TaskController.java             (CRUD + reorder)
│       │   │   ├── HabitController.java            (CRUD + log toggle)
│       │   │   ├── PomodoroController.java         (CRUD)
│       │   │   ├── SleepController.java            (CRUD)
│       │   │   ├── ChatController.java             (rule-based chatbot)
│       │   │   ├── MLInsightsController.java       (analiza statistică + recomandări)
│       │   │   └── MLPredictionController.java     (bridge live către modelul Python)
│       │   ├── model/
│       │   │   ├── User.java
│       │   │   ├── Task.java
│       │   │   ├── Habit.java
│       │   │   ├── HabitLog.java
│       │   │   ├── PomodoroSession.java
│       │   │   ├── SleepLog.java
│       │   │   └── Project.java
│       │   └── repository/
│       │       └── (JpaRepository pentru fiecare model)
│       └── resources/
│           └── application.properties              (DB credentials)
│
├── frontend/
│   ├── package.json
│   ├── app.json                                    (Expo config)
│   ├── app/
│   │   ├── _layout.tsx                             (Stack + ThemeProvider + Gate auto-login)
│   │   ├── index.js                                (Login screen)
│   │   ├── register.js
│   │   ├── onboarding.js                           (3 sliduri)
│   │   ├── pomodoro.js
│   │   └── (tabs)/
│   │       ├── _layout.js                          (tab bar)
│   │       ├── dashboard.js                        (Radar + Tip + Forecast ML + Quick actions)
│   │       ├── tasks.js                            (drag&drop + swipe)
│   │       ├── habits.js
│   │       ├── sleep.js
│   │       ├── progres.js                          (Insights vizibile utilizatorului)
│   │       ├── profile.js                          (theme + achievements + setări)
│   │       └── calendar.js
│   ├── components/
│   │   ├── MyInput.js                              (input text reutilizabil)
│   │   ├── PasswordInput.js                        (input parolă cu toggle ochi)
│   │   └── StatCard.js
│   ├── constants/
│   │   ├── theme.js                                (DARK_COLORS + LIGHT_COLORS)
│   │   └── themeContext.js                         (Provider + useTheme hook)
│   ├── services/
│   │   ├── api.js                                  (axios cu auto-detect IP)
│   │   ├── authState.js                            (persistare user + Remember Me)
│   │   ├── authService.js                          (login/register/update)
│   │   ├── taskService.js
│   │   ├── habitService.js
│   │   ├── pomodoroService.js
│   │   ├── sleepService.js
│   │   ├── chatService.js
│   │   ├── mlService.js                            (getInsights + predict)
│   │   ├── settingsService.js                      (notificări + productive hours)
│   │   └── notificationService.js                  (expo-notifications wrapper)
│   └── utils/
│       ├── validators.js                           (email + parolă + username)
│       ├── achievements.js                         (12 insigne + computeStreak)
│       └── forecast.js                             (mapare scor ML → mesaj natural în 5 praguri)
│
└── ml/
    ├── requirements.txt                            (Python deps)
    ├── README_ML.md
    ├── seed_data.py                                (60-365 zile date test)
    ├── ml_engine.py                                (Ridge + GB + KMeans + PCA, --train + --predict)
    ├── productivity_insights.py                    (analiză + matplotlib)
    ├── models/                                     (modele antrenate .pkl)
    │   └── user_X/
    │       ├── regression.pkl                      (modelul cu cel mai bun R² CV)
    │       ├── scaler.pkl                          (StandardScaler pentru Ridge)
    │       ├── clustering.pkl                      (K-Means antrenat)
    │       ├── cluster_names.json                  (etichetele clusterelor)
    │       └── metadata.json                       (modelul ales + metricile R², MAE, RMSE)
    └── reports/                                    (grafice PNG pentru lucrare)
        └── user_X_regression.png                   (comparație Ridge vs GB)
        └── user_X_feature_importance.png           (top features GB)
        └── user_X_clustering.png                   (Elbow + Silhouette + PCA 2D)
```

---

## 6. CONTRIBUȚII ORIGINALE / DIFERENȚIATORI

Aplicații populare de productivitate comparate (Todoist, TickTick, Notion, Habitica, Forest, MS To Do, Loop, Fabulous, Sleep Cycle, Be Focused) — **niciuna nu reunește toate funcționalitățile de mai jos într-un singur produs**:

1. **Integrare verticală** a celor 4 piloni (sarcini + focus + obiceiuri + somn) într-un model unic de date
2. **Predicție ML live** a productivității zilei următoare prin model antrenat (Gradient Boosting / Ridge) selectat automat prin k-fold cross-validation, cu rezultatul tradus în limbaj natural pentru utilizator
3. **Corelație Pearson** între ore de somn și productivitatea zilei următoare — niciuna dintre aplicațiile analizate nu o calculează
4. **Heatmap zi × interval orar** pentru identificarea ferestrelor optime de lucru
5. **Sistem de recomandări** care transformă cifrele în sfaturi în limba română naturală
6. **Vizualizare RADAR** ca metaforă centrală a productivității zilnice
7. **Interval productiv configurabil** care adaptează semnalele aplicației la programul individual (de ex. student cu cursuri 8-16 setează fereastra 16:00-22:00)
8. **Streak-uri multi-domeniu** (orice activitate contează — nu doar habits ca în Loop)
9. **Trend prin rolling average** și comparație prima jumătate / a doua jumătate
10. **12 insigne tematice** care răsplătesc consistența și progresul cumulativ
11. **Stack tehnologic divers** care demonstrează competențe în 3 limbaje (Java + JavaScript + Python) și 5 zone (backend / mobil / DB / ML / Statistici), legate end-to-end prin bridge live Java ↔ Python

---

## 7. CUM SE RULEAZĂ APLICAȚIA

### Cerințe
- Windows / macOS / Linux
- Java 21 + Maven
- MySQL 8 (rulând pe portul 3306)
- Python 3.11+ cu pip
- Node.js 18+ și npm
- Telefon Android / iOS cu Expo Go instalat
- Toate dispozitivele pe aceeași rețea WiFi

### Pași
1. **Bază de date**: creezi DB `productivity_db` în MySQL (sau e creată automat de Hibernate); actualizezi credențialele în `backend/src/main/resources/application.properties`
2. **Backend**: `cd backend && mvn spring-boot:run` → API live pe `http://localhost:8080`
3. **Dependențele Python**: `cd ml && pip install -r requirements.txt`
4. **Seed date test** (recomandat pentru ML): `python -X utf8 seed_data.py --user 4 --days 365 --clear`
5. **Antrenare modele ML** (necesară pentru cardul Forecast pe dashboard): `python -X utf8 ml_engine.py --user 4 --train` (produce și graficele PNG pentru lucrare)
6. **Frontend**: `cd frontend && npm install && npx expo start -c` → scanezi QR-ul cu Expo Go pe telefon

### Credențiale test
- Email: `silviadum20@gmail.com`
- Parolă: `test12345`
- User ID 4 are 365 zile de date pre-generate cu patternuri clare + modele ML deja antrenate

---

## 8. LIMITĂRI ACTUALE ȘI DEZVOLTĂRI ULTERIOARE

### Limitări
- Modelele ML se antrenează manual prin script Python — nu se reantrenează automat când utilizatorul acumulează date noi
- Asistentul conversațional folosește reguli predefinite, nu un LLM real (deși arhitectura permite extinderea)
- Apelul Python din backend prin `ProcessBuilder` are latență de ~1-2 secunde (acceptabil dar nu instantaneu)
- Aplicația rulează doar local, nu există deployment cloud
- Nu există export PDF al rapoartelor pentru utilizator
- Intervalul productiv este afișat ca chip vizual, dar nu modifică deocamdată comportamentul notificărilor

### Dezvoltări viitoare (capitolul 5 al lucrării)
1. **Reantrenare automată** a modelelor ML când utilizatorul acumulează date noi (cron job sau trigger)
2. **Integrare LLM local** prin Ollama + RAG pentru chatbot conversațional cu date personale (arhitectura este pregătită)
3. **Detecție anomalii** (Isolation Forest) pentru a alerta utilizatorul când productivitatea scade atipic
4. **Predicție pe 7 zile** (multi-step forecast) în loc de doar ziua următoare
5. **Explicabilitate XAI** (SHAP / feature importance per-instanță) pentru a explica utilizatorului de ce a fost făcută o anumită predicție
6. **NLP pe titlurile taskurilor** pentru clasificare automată în categorii
7. **Sincronizare cu Apple HealthKit / Google Fit** pentru import automat al datelor de somn
8. **Export PDF lunar / săptămânal** cu raport personalizat
9. **Versiune web complementară** aplicației mobile
10. **Notificări inteligente** care țin cont de intervalul productiv și de starea utilizatorului
11. **Funcție de goal-setting** cu progres vizual săptămânal/lunar
12. **Deploy în producție** cu Docker + autentificare JWT

---

## 9. METRICILE PROIECTULUI

- **Linii de cod**: ~6,800 LOC distribuite ca:
  - ~2,000 Java (backend, inclusiv MLPredictionController și OllamaService în formă inițială)
  - ~3,500 JavaScript / TSX (frontend)
  - ~1,300 Python (ML + seed + insights)
- **Ecrane în aplicație**: 9 (Login, Register, Onboarding, Dashboard, Tasks, Habits, Pomodoro, Sleep, Progres, Profil)
- **Endpoint-uri REST**: 23 (inclusiv `/api/ml/predict/{userId}` care apelează Python live)
- **Tabele bază de date**: 7
- **Componente reutilizabile**: 6 (PasswordInput, MyInput, StatCard, BarChart, LineChart, Heatmap)
- **Algoritmi de ML / statistică implementați**: 5 (Ridge, Gradient Boosting, K-Means, PCA, Pearson)
- **Modele rulate live în aplicație**: 1 (cel mai bun după k-fold CV, încărcat din `.pkl`)
- **Insigne (achievements)**: 12 niveluri

---

## 10. PUNCTE DE VÂNZARE PENTRU APĂRARE

La întrebarea „**ce face aplicația ta diferit?**", răspunsul scurt:

> „Este singura aplicație care reunește toate cele patru dimensiuni ale productivității personale — sarcini, focus, obiceiuri și somn — într-un singur model de date și care aplică algoritmi de machine learning (Ridge Regression ca baseline liniar și Gradient Boosting ca model nonlinear principal, selectat automat prin k-fold cross-validation), împreună cu clustering nesupervizat (K-Means cu Elbow și Silhouette + PCA pentru vizualizare) și analiză statistică (corelație Pearson), pentru a transforma datele utilizatorului în predicții live și recomandări personalizate, exprimate în limbaj natural. Spre deosebire de aplicații precum Todoist sau Habitica, nu doar afișează cifre, ci explică utilizatorului ce înseamnă ele și sugerează concret ce poate îmbunătăți."

La întrebarea „**unde rulează ML când eu folosesc aplicația?**":

> „Modelele de Gradient Boosting și Ridge Regression se antrenează offline în Python prin scriptul `ml_engine.py` și se salvează ca artefacte `.pkl` folosind joblib. Selecția modelului final se face automat prin k-fold cross-validation (k=5), iar cel cu cel mai bun R² mediu este folosit pentru predicție. La fiecare deschidere a dashboard-ului, backend-ul Spring apelează scriptul Python printr-un `ProcessBuilder`, modelul antrenat e încărcat și face inferență cu vectorul curent de caracteristici (lag features, rolling mean, cyclical encoding al zilei săptămânii, ore și calitate somn). Rezultatul predicției este transformat de frontend, prin utilitar `forecast.js`, într-un mesaj natural în limba română prin 5 praguri — utilizatorul vede un sfat prietenos, nu cifre. Această decizie de design urmează modelul aplicațiilor moderne (Spotify, Netflix) unde algoritmii complecși sunt ascunși în spatele unei interfețe simple."

La întrebarea „**de ce nu ai folosit LLM / GPT?**":

> „Am evaluat integrarea unui LLM local prin Ollama cu arhitectură RAG. Am decis însă să rămân pe ML clasic pentru două motive: (1) controlul total al răspunsurilor — un model lingvistic poate halucina cifre incorecte, iar într-o aplicație care îți afișează date reale despre sănătate și productivitate, acuratețea e mai importantă decât naturalețea; (2) simplitatea demonstrației — eliminarea unei dependențe externe reduce riscul de eșec la apărare. Integrarea LLM este menționată în capitolul de dezvoltări viitoare."
