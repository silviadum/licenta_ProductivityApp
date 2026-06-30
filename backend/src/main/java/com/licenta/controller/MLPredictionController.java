package com.licenta.controller;

import com.licenta.repository.PomodoroRepository;
import com.licenta.repository.SleepLogRepository;
import com.licenta.repository.TaskRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.attribute.BasicFileAttributes;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Controller pentru predicția productivității + ANTRENARE AUTOMATĂ în background.
 *
 * Comportament:
 *   - GET /api/ml/predict/{userId}:
 *       1. Dacă există model antrenat → predicție live, returnează clasa + confidence
 *       2. Dacă NU există model + user are ≥ 30 zile de date → antrenare automată
 *          în background, returnează { available: false, training: true }
 *       3. Dacă există model dar e mai vechi de 30 zile → reantrenare automată
 *          în background (predicția curentă folosește modelul vechi pentru această cerere)
 *
 * Antrenarea rulează într-un thread pool separat — nu blochează niciodată cererea HTTP.
 */
@RestController
@RequestMapping("/api/ml")
@CrossOrigin(origins = "*")
public class MLPredictionController {

    private static final String ML_DIR = "D:/licenta/ProductivityApp/ml";
    private static final int MIN_DAYS_FOR_TRAINING = 30;       // prag minim pentru antrenare automată
    private static final int STALE_MODEL_DAYS = 30;            // prag pentru reantrenare automată

    // Thread pool pentru antrenare în background (max 2 simultan ca să nu suprasolicităm CPU)
    private static final ExecutorService TRAINING_POOL = Executors.newFixedThreadPool(2);

    // Set de user-ID-uri pentru care antrenarea e deja în curs (evită dublarea)
    private static final Set<Long> TRAINING_IN_PROGRESS = ConcurrentHashMap.newKeySet();

    @Autowired private TaskRepository       taskRepo;
    @Autowired private PomodoroRepository   pomoRepo;
    @Autowired private SleepLogRepository   sleepRepo;

    @GetMapping("/predict/{userId}")
    public Map<String, Object> predict(@PathVariable Long userId) {
        Map<String, Object> result = new HashMap<>();
        Path classifierPath = Paths.get(ML_DIR, "models", "user_" + userId, "classifier.pkl");

        // ─── CAZUL 1: Nu există model antrenat ────────────────────────────────
        if (!Files.exists(classifierPath)) {
            int activeDays = countActiveDays(userId);

            if (activeDays >= MIN_DAYS_FOR_TRAINING) {
                // User are date suficiente — antrenez automat în background
                boolean started = triggerBackgroundTraining(userId);
                result.put("available", false);
                result.put("training", started);
                result.put("days_collected", activeDays);
                result.put("message", started
                        ? "Modelul tău se antrenează în background. Vino înapoi în câteva minute."
                        : "Antrenarea e deja în curs.");
                return result;
            } else {
                // Date insuficiente
                result.put("available", false);
                result.put("training", false);
                result.put("days_collected", activeDays);
                result.put("days_needed", MIN_DAYS_FOR_TRAINING);
                result.put("message", "Mai folosește aplicația. Predicțiile personalizate se activează după "
                        + MIN_DAYS_FOR_TRAINING + " zile (ai " + activeDays + ").");
                return result;
            }
        }

        // ─── CAZUL 2: Modelul există dar e mai vechi de 30 zile → reantrenare ─
        try {
            BasicFileAttributes attrs = Files.readAttributes(classifierPath, BasicFileAttributes.class);
            Instant modifiedTime = attrs.lastModifiedTime().toInstant();
            long ageDays = Duration.between(modifiedTime, Instant.now()).toDays();
            if (ageDays > STALE_MODEL_DAYS) {
                triggerBackgroundTraining(userId);  // reantrenare; folosim modelul vechi pentru acest request
                result.put("model_age_days", ageDays);
                result.put("retraining", true);
            }
        } catch (IOException ignored) {
            // Nu blocăm predicția dacă nu putem citi atributele
        }

        // ─── CAZUL 3: Predicție normală cu modelul existent ──────────────────
        return runPrediction(userId, result);
    }

    /**
     * Numără zilele distincte cu activitate ale utilizatorului
     * (taskuri completate, sesiuni Pomodoro, înregistrări de somn).
     */
    private int countActiveDays(Long userId) {
        Set<LocalDate> uniqueDays = new HashSet<>();

        taskRepo.findByUserId(userId).stream()
                .filter(t -> "DONE".equals(t.getStatus()) && t.getCompletedAt() != null)
                .forEach(t -> uniqueDays.add(t.getCompletedAt().toLocalDate()));

        pomoRepo.findByUserIdOrderByStartTimeDesc(userId).stream()
                .filter(p -> p.isWasCompleted() && p.getStartTime() != null)
                .forEach(p -> uniqueDays.add(p.getStartTime().toLocalDate()));

        sleepRepo.findByUserIdOrderByLogDateDesc(userId).stream()
                .filter(s -> s.getLogDate() != null)
                .forEach(s -> uniqueDays.add(s.getLogDate()));

        return uniqueDays.size();
    }

    /**
     * Pornește antrenarea în background.
     * @return true dacă a pornit, false dacă era deja în curs pentru acest user
     */
    private boolean triggerBackgroundTraining(Long userId) {
        if (!TRAINING_IN_PROGRESS.add(userId)) {
            return false; // deja în curs
        }

        TRAINING_POOL.submit(() -> {
            System.out.println("[ML AutoTrain] Start antrenare pentru user " + userId);
            try {
                ProcessBuilder pb = new ProcessBuilder(
                        "python", "-X", "utf8",
                        "ml_engine.py",
                        "--user", String.valueOf(userId),
                        "--train",
                        "--no-plot"  // sărim peste grafice ca să fie mai rapid
                );
                pb.directory(new File(ML_DIR));
                pb.redirectErrorStream(true);
                pb.environment().put("PYTHONIOENCODING", "utf-8");

                Process p = pb.start();
                StringBuilder output = new StringBuilder();
                try (BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8))) {
                    String line;
                    while ((line = br.readLine()) != null) output.append(line).append("\n");
                }
                int exitCode = p.waitFor();
                System.out.println("[ML AutoTrain] Antrenare user " + userId + " terminata, exitCode=" + exitCode);
            } catch (Exception e) {
                System.err.println("[ML AutoTrain] Eroare user " + userId + ": " + e.getMessage());
            } finally {
                TRAINING_IN_PROGRESS.remove(userId);
            }
        });
        return true;
    }

    /**
     * Rulează scriptul Python pentru predicție și parsează output-ul.
     */
    private Map<String, Object> runPrediction(Long userId, Map<String, Object> baseResult) {
        try {
            ProcessBuilder pb = new ProcessBuilder(
                    "python", "-X", "utf8",
                    "ml_engine.py",
                    "--user", String.valueOf(userId),
                    "--predict"
            );
            pb.directory(new File(ML_DIR));
            pb.redirectErrorStream(true);
            pb.environment().put("PYTHONIOENCODING", "utf-8");

            Process p = pb.start();
            StringBuilder out = new StringBuilder();
            try (BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = br.readLine()) != null) out.append(line).append("\n");
            }
            p.waitFor();

            String output = out.toString();
            String predictedClass = null;
            String predictedLabel = null;
            Double confidence = null;
            Double probSlaba = null, probNormala = null, probBuna = null;

            Pattern classPattern = Pattern.compile("Clasa estimata:\\s*(\\S+)\\s*\\((\\S+)\\)");
            Pattern confPattern  = Pattern.compile("Increderea:\\s*([0-9.]+)");
            Pattern slabaPattern = Pattern.compile("SLABA:\\s*([0-9.]+)");
            Pattern normalaPattern = Pattern.compile("NORMALA:\\s*([0-9.]+)");
            Pattern bunaPattern  = Pattern.compile("BUNA:\\s*([0-9.]+)");

            for (String line : output.split("\n")) {
                Matcher m1 = classPattern.matcher(line);
                if (m1.find()) {
                    predictedLabel = m1.group(1);
                    predictedClass = m1.group(2);
                }
                Matcher m2 = confPattern.matcher(line);
                if (m2.find()) {
                    try { confidence = Double.parseDouble(m2.group(1)) / 100.0; } catch (Exception ignored) {}
                }
                Matcher m3 = slabaPattern.matcher(line);
                if (m3.find()) try { probSlaba = Double.parseDouble(m3.group(1)) / 100.0; } catch (Exception ignored) {}
                Matcher m4 = normalaPattern.matcher(line);
                if (m4.find()) try { probNormala = Double.parseDouble(m4.group(1)) / 100.0; } catch (Exception ignored) {}
                Matcher m5 = bunaPattern.matcher(line);
                if (m5.find()) try { probBuna = Double.parseDouble(m5.group(1)) / 100.0; } catch (Exception ignored) {}
            }

            if (predictedClass != null) {
                baseResult.put("available", true);
                baseResult.put("predicted_class", predictedClass);
                baseResult.put("predicted_label", predictedLabel);
                baseResult.put("confidence", confidence != null ? confidence : 0.0);
                Map<String, Double> probs = new HashMap<>();
                if (probSlaba != null) probs.put("SLABA", probSlaba);
                if (probNormala != null) probs.put("NORMALA", probNormala);
                if (probBuna != null) probs.put("BUNA", probBuna);
                baseResult.put("probabilities", probs);
            } else {
                baseResult.put("available", false);
            }

        } catch (Exception e) {
            baseResult.put("available", false);
            baseResult.put("error", e.getMessage());
        }

        return baseResult;
    }
}
