package com.licenta.controller;

import com.licenta.model.*;
import com.licenta.repository.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.time.*;
import java.time.temporal.ChronoUnit;
import java.util.*;

/**
 * Endpoint care calculează insights / recomandări pe baza datelor reale ale userului.
 * Returnează un singur JSON cu tot ce-i trebuie ecranului de Insights ca să randeze grafice + sfaturi.
 *
 * Acoperă paritate completă cu scriptul Python `ml/productivity_insights.py`.
 */
@RestController
@RequestMapping("/api/ml")
@CrossOrigin(origins = "*")
public class MLInsightsController {

    @Autowired private TaskRepository taskRepo;
    @Autowired private HabitRepository habitRepo;
    @Autowired private HabitLogRepository habitLogRepo;
    @Autowired private PomodoroRepository pomoRepo;
    @Autowired private SleepLogRepository sleepRepo;

    @GetMapping("/insights/{userId}")
    public Map<String, Object> insights(@PathVariable Long userId) {
        Map<String, Object> out = new LinkedHashMap<>();

        List<Task> tasks      = taskRepo.findByUserId(userId);
        List<Habit> habits    = habitRepo.findByUserId(userId);
        List<Long> habitIds   = habits.stream().map(Habit::getId).toList();
        List<HabitLog> hlogs  = habitIds.isEmpty() ? List.of() : habitLogRepo.findByHabitIdIn(habitIds);
        List<PomodoroSession> pomos = pomoRepo.findByUserIdOrderByStartTimeDesc(userId);
        List<SleepLog> sleep  = sleepRepo.findByUserIdOrderByLogDateDesc(userId);

        int nHabits = habits.size();

        // ── 1. Activitate per oră (0-23) ──────────────────────────────────────
        double[] hourCounts = new double[24];
        for (Task t : tasks) {
            if ("DONE".equals(t.getStatus()) && t.getCompletedAt() != null) {
                hourCounts[t.getCompletedAt().getHour()] += 1;
            }
        }
        for (PomodoroSession p : pomos) {
            if (p.isWasCompleted() && p.getStartTime() != null) {
                hourCounts[p.getStartTime().getHour()] += 0.6; // sesiuni cântăresc puțin mai puțin
            }
        }
        List<Map<String, Object>> hourData = new ArrayList<>();
        for (int h = 0; h < 24; h++) {
            hourData.add(Map.of("hour", h, "value", Math.round(hourCounts[h] * 10) / 10.0));
        }
        out.put("hourActivity", hourData);

        // ── 2. Best time block + procent ─────────────────────────────────────
        Map<String, Double> blocks = new LinkedHashMap<>();
        blocks.put("Dimineață", 0.0);
        blocks.put("După-amiază", 0.0);
        blocks.put("Seară", 0.0);
        blocks.put("Noapte", 0.0);
        for (Task t : tasks) {
            if ("DONE".equals(t.getStatus()) && t.getCompletedAt() != null) {
                blocks.merge(blockFor(t.getCompletedAt().getHour()), 1.0, Double::sum);
            }
        }
        for (PomodoroSession p : pomos) {
            if (p.isWasCompleted() && p.getStartTime() != null) {
                blocks.merge(blockFor(p.getStartTime().getHour()), 0.6, Double::sum);
            }
        }
        double blockTotal = blocks.values().stream().mapToDouble(Double::doubleValue).sum();
        String bestBlock = blocks.entrySet().stream()
                .max(Map.Entry.comparingByValue()).map(Map.Entry::getKey).orElse(null);
        double bestBlockPct = bestBlock != null && blockTotal > 0
                ? Math.round(100 * blocks.get(bestBlock) / blockTotal) : 0;
        out.put("bestTimeBlock", bestBlock);
        out.put("bestTimeBlockPercent", bestBlockPct);
        out.put("timeBlocks", blocks.entrySet().stream()
                .map(e -> Map.of("label", e.getKey(), "value", Math.round(e.getValue())))
                .toList());

        // ── 3. Score / zi calendaristică ─────────────────────────────────────
        Map<LocalDate, double[]> dayBuckets = new HashMap<>(); // [tasks, habits, pomos, pomoMin]
        for (Task t : tasks) {
            if ("DONE".equals(t.getStatus()) && t.getCompletedAt() != null) {
                dayBuckets.computeIfAbsent(t.getCompletedAt().toLocalDate(), k -> new double[4])[0]++;
            }
        }
        for (HabitLog hl : hlogs) {
            if (hl.getDateCompleted() != null) {
                dayBuckets.computeIfAbsent(hl.getDateCompleted(), k -> new double[4])[1]++;
            }
        }
        for (PomodoroSession p : pomos) {
            if (p.isWasCompleted() && p.getStartTime() != null) {
                double[] arr = dayBuckets.computeIfAbsent(p.getStartTime().toLocalDate(), k -> new double[4]);
                arr[2]++;
                arr[3] += p.getDurationMinutes();
            }
        }
        // Scor brut, apoi normalizez 0-100 pe maximul perioadei
        Map<LocalDate, Double> rawScore = new HashMap<>();
        for (var e : dayBuckets.entrySet()) {
            double[] v = e.getValue();
            double habitRatio = nHabits > 0 ? v[1] / nHabits : 0;
            double raw = v[0] * 4 + habitRatio * 30 + v[2] * 5 + (v[3] / 60.0) * 8;
            rawScore.put(e.getKey(), raw);
        }
        double maxRaw = rawScore.values().stream().mapToDouble(Double::doubleValue).max().orElse(0);
        Map<LocalDate, Double> dayScore = new HashMap<>();
        for (var e : rawScore.entrySet()) {
            double normalized = maxRaw > 0 ? e.getValue() / maxRaw * 100 : 0;
            dayScore.put(e.getKey(), Math.round(normalized * 10) / 10.0);
        }

        // ── 4. Best & WORST weekday ──────────────────────────────────────────
        double[] sumScore = new double[7];
        int[] cntScore    = new int[7];
        for (var e : dayScore.entrySet()) {
            int dow = e.getKey().getDayOfWeek().getValue() - 1;
            sumScore[dow] += e.getValue();
            cntScore[dow]++;
        }
        String[] WD_RO = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"};
        String[] WD_SHORT = {"M", "T", "W", "T", "F", "S", "S"};
        List<Map<String, Object>> wd = new ArrayList<>();
        int bestWd = -1; double bestWdVal = -1;
        int worstWd = -1; double worstWdVal = Double.MAX_VALUE;
        for (int i = 0; i < 7; i++) {
            double val = cntScore[i] > 0 ? sumScore[i] / cntScore[i] : 0;
            wd.add(Map.of("label", WD_SHORT[i], "fullLabel", WD_RO[i], "value", Math.round(val), "n", cntScore[i]));
            if (cntScore[i] > 0 && val > bestWdVal) { bestWdVal = val; bestWd = i; }
            if (cntScore[i] > 0 && val < worstWdVal) { worstWdVal = val; worstWd = i; }
        }
        out.put("weekdayScores", wd);
        out.put("bestWeekday", bestWd >= 0 ? WD_RO[bestWd] : null);
        out.put("bestWeekdayScore", bestWd >= 0 ? Math.round(bestWdVal) : null);
        out.put("worstWeekday", worstWd >= 0 && bestWd != worstWd ? WD_RO[worstWd] : null);
        out.put("worstWeekdayScore", worstWd >= 0 ? Math.round(worstWdVal) : null);

        // ── 5. Pomodoro per durată + scurte vs lungi ─────────────────────────
        String[] DUR_LABELS = {"≤20m", "21-30m", "31-45m", ">45m"};
        int[] durDone = new int[4];
        int[] durTotal = new int[4];
        for (PomodoroSession p : pomos) {
            int dur = p.getDurationMinutes();
            int idx = dur <= 20 ? 0 : dur <= 30 ? 1 : dur <= 45 ? 2 : 3;
            durTotal[idx]++;
            if (p.isWasCompleted()) durDone[idx]++;
        }
        List<Map<String, Object>> dur = new ArrayList<>();
        int bestDurIdx = 0; int bestDurDone = -1;
        for (int i = 0; i < 4; i++) {
            int rate = durTotal[i] > 0 ? Math.round(100f * durDone[i] / durTotal[i]) : 0;
            dur.add(Map.of("label", DUR_LABELS[i], "done", durDone[i], "total", durTotal[i], "rate", rate));
            if (durDone[i] > bestDurDone) { bestDurDone = durDone[i]; bestDurIdx = i; }
        }
        out.put("pomoDurations", dur);
        out.put("bestPomoDuration", bestDurDone > 0 ? DUR_LABELS[bestDurIdx] : null);

        // Sesiuni scurte (≤25m) vs lungi (≥40m)
        int shortDone = 0, shortTotal = 0, longDone = 0, longTotal = 0;
        int avgDurSum = 0, avgDurCount = 0;
        for (PomodoroSession p : pomos) {
            int d = p.getDurationMinutes();
            if (d <= 25) {
                shortTotal++;
                if (p.isWasCompleted()) shortDone++;
            }
            if (d >= 40) {
                longTotal++;
                if (p.isWasCompleted()) longDone++;
            }
            if (p.isWasCompleted()) {
                avgDurSum += d;
                avgDurCount++;
            }
        }
        if (shortTotal >= 2 && longTotal >= 2) {
            int sR = Math.round(100f * shortDone / shortTotal);
            int lR = Math.round(100f * longDone / longTotal);
            Map<String, Object> svl = new LinkedHashMap<>();
            svl.put("shortRate", sR);
            svl.put("longRate", lR);
            svl.put("winner", sR >= lR ? "short" : "long");
            svl.put("shortLabel", "≤25m");
            svl.put("longLabel", "≥40m");
            out.put("pomoShortVsLong", svl);
        }
        out.put("avgCompletedPomoDuration", avgDurCount > 0 ? Math.round((double) avgDurSum / avgDurCount) : null);

        // ── 6. Ore somn → scor zi următoare + corelație ──────────────────────
        String[] SLP_LABELS = {"<6h", "6-7h", "7-8h", "8-9h", ">9h"};
        double[] slpSum = new double[5];
        int[] slpCnt = new int[5];
        double avgSleep = 0; int avgCnt = 0;
        List<Double> sleepHoursList = new ArrayList<>();
        List<Double> sleepNextDayScores = new ArrayList<>();
        List<Double> sleepQualityList = new ArrayList<>();
        List<Double> qualityNextDayScores = new ArrayList<>();
        // Pentru chart-ul calitate vs scor:
        Map<Integer, double[]> qualityBuckets = new TreeMap<>(); // qual → [sum, count]

        for (SleepLog s : sleep) {
            if (s.getBedtime() == null || s.getWakeUpTime() == null) continue;
            double hours = ChronoUnit.MINUTES.between(s.getBedtime(), s.getWakeUpTime()) / 60.0;
            if (hours <= 0 || hours > 16) continue;
            avgSleep += hours; avgCnt++;
            int idx = hours < 6 ? 0 : hours < 7 ? 1 : hours < 8 ? 2 : hours < 9 ? 3 : 4;
            LocalDate next = s.getLogDate() == null ? null : s.getLogDate().plusDays(1);
            Double score = next != null ? dayScore.get(next) : null;
            if (score != null) {
                slpSum[idx] += score; slpCnt[idx]++;
                sleepHoursList.add(hours);
                sleepNextDayScores.add(score);
                if (s.getQualityScore() != null) {
                    sleepQualityList.add((double) s.getQualityScore());
                    qualityNextDayScores.add(score);
                    double[] qb = qualityBuckets.computeIfAbsent(s.getQualityScore(), k -> new double[2]);
                    qb[0] += score; qb[1]++;
                }
            }
        }
        List<Map<String, Object>> slp = new ArrayList<>();
        int bestSlpIdx = -1; double bestSlpVal = -1;
        for (int i = 0; i < 5; i++) {
            double val = slpCnt[i] > 0 ? slpSum[i] / slpCnt[i] : 0;
            slp.add(Map.of("label", SLP_LABELS[i], "value", Math.round(val), "n", slpCnt[i]));
            if (slpCnt[i] > 0 && val > bestSlpVal) { bestSlpVal = val; bestSlpIdx = i; }
        }
        out.put("sleepHours", slp);
        out.put("bestSleepHours", bestSlpIdx >= 0 ? SLP_LABELS[bestSlpIdx] : null);
        out.put("avgSleepHours", avgCnt > 0 ? Math.round(10.0 * avgSleep / avgCnt) / 10.0 : null);

        out.put("sleepCorrelation", pearson(sleepHoursList, sleepNextDayScores));
        out.put("sleepQualityCorrelation", pearson(sleepQualityList, qualityNextDayScores));

        // Quality scores chart: pentru fiecare nivel de calitate, scor mediu + n
        List<Map<String, Object>> qualityScores = new ArrayList<>();
        for (var e : qualityBuckets.entrySet()) {
            double[] v = e.getValue();
            qualityScores.add(Map.of(
                    "quality", e.getKey(),
                    "score", Math.round(v[0] / v[1]),
                    "n", (int) v[1]
            ));
        }
        out.put("qualityScores", qualityScores);

        // ── 7. Heatmap zi×interval (matrice 7×4) ─────────────────────────────
        int[][] heat = new int[7][4];
        BiToInt assignBlock = (h) -> h >= 5 && h < 12 ? 0 : h >= 12 && h < 17 ? 1 : h >= 17 && h < 22 ? 2 : 3;
        for (Task t : tasks) {
            if ("DONE".equals(t.getStatus()) && t.getCompletedAt() != null) {
                int dow = t.getCompletedAt().getDayOfWeek().getValue() - 1;
                heat[dow][assignBlock.apply(t.getCompletedAt().getHour())]++;
            }
        }
        for (PomodoroSession p : pomos) {
            if (p.isWasCompleted() && p.getStartTime() != null) {
                int dow = p.getStartTime().getDayOfWeek().getValue() - 1;
                heat[dow][assignBlock.apply(p.getStartTime().getHour())]++;
            }
        }
        out.put("heatmap", heat);

        // ── 8. Streak ────────────────────────────────────────────────────────
        int streak = 0;
        LocalDate cursor = LocalDate.now();
        while (true) {
            Double sc = dayScore.get(cursor);
            if (cursor.equals(LocalDate.now()) && (sc == null || sc == 0)) {
                cursor = cursor.minusDays(1);
                continue;
            }
            if (sc != null && sc > 0) { streak++; cursor = cursor.minusDays(1); }
            else break;
        }
        out.put("streak", streak);

        // ── 9. Productivity timeline (ultimele ~60 zile cu rolling avg 7) ────
        List<LocalDate> sortedDates = new ArrayList<>(dayScore.keySet());
        Collections.sort(sortedDates);
        List<Map<String, Object>> timeline = new ArrayList<>();
        for (int i = 0; i < sortedDates.size(); i++) {
            LocalDate d = sortedDates.get(i);
            double v = dayScore.get(d);
            // rolling avg pe ultimele 7 puncte (inclusiv curent)
            int from = Math.max(0, i - 6);
            double sum = 0; int cnt = 0;
            for (int j = from; j <= i; j++) {
                sum += dayScore.get(sortedDates.get(j));
                cnt++;
            }
            double rolling = cnt > 0 ? sum / cnt : v;
            Map<String, Object> point = new LinkedHashMap<>();
            point.put("date", d.toString());
            point.put("score", Math.round(v));
            point.put("rolling7", Math.round(rolling * 10) / 10.0);
            timeline.add(point);
        }
        out.put("productivityTimeline", timeline);

        // ── 10. Trend (prima jumătate vs a doua jumătate) ────────────────────
        if (sortedDates.size() >= 7) {
            int half = sortedDates.size() / 2;
            double firstAvg = sortedDates.subList(0, half).stream()
                    .mapToDouble(dayScore::get).average().orElse(0);
            double secondAvg = sortedDates.subList(half, sortedDates.size()).stream()
                    .mapToDouble(dayScore::get).average().orElse(0);
            double diff = secondAvg - firstAvg;
            String direction = Math.abs(diff) < 3 ? "flat" : (diff > 0 ? "up" : "down");
            out.put("trend", Map.of(
                    "firstHalf", Math.round(firstAvg),
                    "secondHalf", Math.round(secondAvg),
                    "diff", Math.round(diff * 10) / 10.0,
                    "direction", direction
            ));
        }

        // ── 11. Habit rate (rata medie de completare) ────────────────────────
        if (nHabits > 0 && !sortedDates.isEmpty()) {
            double totalRatio = 0; int activeDays = 0;
            for (LocalDate d : sortedDates) {
                double[] v = dayBuckets.get(d);
                if (v != null) {
                    totalRatio += v[1] / nHabits;
                    activeDays++;
                }
            }
            int avgRate = activeDays > 0 ? (int) Math.round(100.0 * totalRatio / activeDays) : 0;
            out.put("habitAverageRate", avgRate);
        }

        // ── 12. Total stats ──────────────────────────────────────────────────
        long tasksDone = tasks.stream().filter(t -> "DONE".equals(t.getStatus())).count();
        long pomoDone  = pomos.stream().filter(PomodoroSession::isWasCompleted).count();
        int focusMin   = pomos.stream().filter(PomodoroSession::isWasCompleted)
                .mapToInt(PomodoroSession::getDurationMinutes).sum();
        out.put("totalTasksDone", tasksDone);
        out.put("totalPomoDone", pomoDone);
        out.put("totalFocusMin", focusMin);
        out.put("totalSleepLogs", sleep.size());
        out.put("activeDays", sortedDates.size());

        // ── 13. Personalized recommendations ─────────────────────────────────
        List<String> recs = new ArrayList<>();
        if (bestBlock != null && tasksDone >= 3) {
            String blockEn = blockToEnglish(bestBlock);
            recs.add("You're most productive in the " + blockEn + " (" + (int) bestBlockPct + "% of your activity). Schedule your important tasks then.");
        }
        if (out.get("bestWeekday") != null) {
            recs.add("Your top day is " + out.get("bestWeekday") + ". Use it for deep work, not meetings.");
        }
        if (out.get("worstWeekday") != null) {
            recs.add(out.get("worstWeekday") + " is your slowest day — plan light tasks or rest.");
        }
        if (out.get("pomoShortVsLong") != null) {
            @SuppressWarnings("unchecked")
            Map<String, Object> svl = (Map<String, Object>) out.get("pomoShortVsLong");
            String winner = (String) svl.get("winner");
            int wRate = (int) svl.get(winner + "Rate");
            int lRate = winner.equals("short") ? (int) svl.get("longRate") : (int) svl.get("shortRate");
            String wLabel = winner.equals("short") ? "short (≤25m)" : "long (≥40m)";
            recs.add(wLabel + " sessions work better for you: " + wRate + "% vs " + lRate + "%. Set this as your default duration in profile.");
        }
        Object pearsonObj = out.get("sleepCorrelation");
        if (pearsonObj instanceof Number p && Math.abs(p.doubleValue()) > 0.20) {
            if (p.doubleValue() > 0) {
                recs.add(String.format(Locale.ROOT,
                        "More sleep → more productivity (correlation +%.2f). Aim for %s.",
                        p.doubleValue(), out.getOrDefault("bestSleepHours", "7-8h")));
            } else {
                recs.add(String.format(Locale.ROOT,
                        "Watch out: too much sleep seems to lower your productivity (correlation %.2f). Optimal: %s.",
                        p.doubleValue(), out.getOrDefault("bestSleepHours", "7-8h")));
            }
        }
        Object qualPearson = out.get("sleepQualityCorrelation");
        if (qualPearson instanceof Number q && Math.abs(q.doubleValue()) > 0.20) {
            String dirText = q.doubleValue() > 0 ? "rises" : "drops";
            recs.add(String.format(Locale.ROOT,
                    "Sleep quality ↔ productivity: r=%+.2f — your productivity %s with sleep quality.",
                    q.doubleValue(), dirText));
        }
        if (avgCnt > 0) {
            double avg = avgSleep / avgCnt;
            if (avg < 6.5) recs.add("Your average sleep (" + Math.round(avg * 10) / 10.0 + "h) is below the recommendation. Aim for at least 7h.");
            else if (avg > 9.0) recs.add("You sleep more than 9h on average — check whether it's quality or just time in bed.");
        }
        Object hrate = out.get("habitAverageRate");
        if (hrate instanceof Integer hr) {
            if (hr < 50) recs.add("Your habit completion rate is " + hr + "%. Cut down to 2-3 easy habits to build consistency.");
            else if (hr >= 80) recs.add("Strong habits (" + hr + "% completion). Add a new one when you feel ready.");
        }
        Object trendObj = out.get("trend");
        if (trendObj instanceof Map<?, ?> trendMap) {
            String dir = (String) trendMap.get("direction");
            Object diff = trendMap.get("diff");
            if ("up".equals(dir)) recs.add("📈 Your productivity is on the rise (+" + diff + " points compared to the start). Keep it up!");
            else if ("down".equals(dir)) recs.add("📉 Your productivity is dropping (" + diff + " points). Rethink your weekly routine.");
        }
        if (streak >= 3) {
            recs.add("🔥 You're on a " + streak + "-day streak. Don't break it — do at least one small task today.");
        }
        if (tasksDone < 3 && pomoDone < 3) {
            recs.add("Not enough data yet. Add activities for ~7-10 days to get quality recommendations.");
        }
        out.put("recommendations", recs);

        return out;
    }

    // ── Helpers ────────────────────────────────────────────────────────────────
    private static String blockFor(int h) {
        if (h >= 5 && h < 12) return "Morning";
        if (h >= 12 && h < 17) return "Afternoon";
        if (h >= 17 && h < 22) return "Evening";
        return "Night";
    }

    private static String blockToEnglish(String roBlock) {
        // Already English now — passthrough for safety in case of legacy data
        return roBlock.toLowerCase(Locale.ROOT);
    }

    private static String weekdayToEnglish(String roDay) {
        switch (roDay) {
            case "Luni":     return "Monday";
            case "Marți":    return "Tuesday";
            case "Miercuri": return "Wednesday";
            case "Joi":      return "Thursday";
            case "Vineri":   return "Friday";
            case "Sâmbătă":  return "Saturday";
            case "Duminică": return "Sunday";
            default:         return roDay;
        }
    }

    private static Double pearson(List<Double> xs, List<Double> ys) {
        int n = xs.size();
        if (n < 3) return null;
        double mx = xs.stream().mapToDouble(Double::doubleValue).average().orElse(0);
        double my = ys.stream().mapToDouble(Double::doubleValue).average().orElse(0);
        double num = 0, dx = 0, dy = 0;
        for (int i = 0; i < n; i++) {
            double a = xs.get(i) - mx, b = ys.get(i) - my;
            num += a * b; dx += a * a; dy += b * b;
        }
        double den = Math.sqrt(dx * dy);
        if (den == 0) return null;
        return Math.round(num / den * 100.0) / 100.0;
    }

    @FunctionalInterface
    private interface BiToInt { int apply(int h); }
}
