package com.licenta.controller;

import org.springframework.web.bind.annotation.*;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Map;

/**
 * Controller pentru predicția productivității folosind modelul ML antrenat.
 *
 * Apelează scriptul Python `ml_engine.py --predict` și returnează scorul prezis.
 *
 * Endpoint:
 *   GET /api/ml/predict/{userId}
 *
 * Note:
 *   - Modelul trebuie antrenat în prealabil cu:
 *       python ml_engine.py --user {userId} --train
 *   - Dacă modelul nu există, endpoint-ul returnează { available: false }
 *   - Frontend-ul folosește predicția DOAR pentru a afișa un mesaj natural,
 *     nu cifre raw (decizie de design UX).
 */
@RestController
@RequestMapping("/api/ml")
@CrossOrigin(origins = "*")
public class MLPredictionController {

    private static final String ML_DIR = "D:/licenta/ProductivityApp/ml";

    @GetMapping("/predict/{userId}")
    public Map<String, Object> predict(@PathVariable Long userId) {
        Map<String, Object> result = new HashMap<>();

        // Verifică dacă există modelul antrenat
        Path modelPath = Paths.get(ML_DIR, "models", "user_" + userId, "regression.pkl");
        if (!Files.exists(modelPath)) {
            result.put("available", false);
            return result;
        }

        // Apelează scriptul Python pentru predicție
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

            // Parsing linii cu cifrele relevante
            String output = out.toString();
            Double predicted = null;
            Double recentAvg = null;

            for (String line : output.split("\n")) {
                if (line.contains("Scor estimat:")) {
                    String num = line.replaceAll(".*Scor estimat:\\s*([0-9.]+).*", "$1");
                    try { predicted = Double.parseDouble(num); } catch (Exception ignored) {}
                }
                if (line.contains("Media ultimelor")) {
                    String num = line.replaceAll(".*:\\s*([0-9.]+).*", "$1");
                    try { recentAvg = Double.parseDouble(num); } catch (Exception ignored) {}
                }
            }

            if (predicted != null) {
                result.put("available", true);
                result.put("predicted_score", predicted);
                result.put("recent_avg", recentAvg != null ? recentAvg : predicted);
                result.put("delta", recentAvg != null ? predicted - recentAvg : 0.0);
            } else {
                result.put("available", false);
            }

        } catch (Exception e) {
            result.put("available", false);
            result.put("error", e.getMessage());
        }

        return result;
    }
}
