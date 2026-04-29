package com.licenta.controller;

import com.licenta.model.*;
import com.licenta.repository.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/chat")
@CrossOrigin(origins = "*")
public class ChatController {

    @Autowired private TaskRepository       taskRepository;
    @Autowired private HabitRepository      habitRepository;
    @Autowired private HabitLogRepository   habitLogRepository;
    @Autowired private PomodoroRepository   pomodoroRepository;
    @Autowired private SleepLogRepository   sleepLogRepository;

    private static final Random RNG = new Random();

    // ── POST /api/chat/message ────────────────────────────────────────────────
    @PostMapping("/message")
    public ResponseEntity<Map<String, String>> message(@RequestBody Map<String, Object> body) {
        Long   userId  = Long.valueOf(body.get("userId").toString());
        String message = body.get("message").toString().toLowerCase(Locale.ROOT).trim();
        return ResponseEntity.ok(Map.of("reply", generateReply(userId, message)));
    }

    // ── GET /api/chat/proactive/{userId} ─────────────────────────────────────
    @GetMapping("/proactive/{userId}")
    public ResponseEntity<Map<String, String>> proactive(@PathVariable Long userId) {
        return ResponseEntity.ok(Map.of("message", generateProactive(userId)));
    }

    // ════════════════════════════════════════════════════════════════════════
    // REPLY GENERATOR
    // ════════════════════════════════════════════════════════════════════════

    private String generateReply(Long userId, String msg) {
        LocalDate today = LocalDate.now();

        // ── Greeting ──────────────────────────────────────────────────────────
        if (has(msg, "salut","buna","bună","hey","hello","ciao","hi","hy")) {
            long todo = taskRepository.findByUserId(userId).stream()
                .filter(t -> "TODO".equals(t.getStatus())).count();
            String extra = todo > 0
                ? " Ai " + todo + " task" + (todo == 1 ? "" : "-uri") + " de rezolvat!"
                : " Totul pare în ordine!";
            return "👋 Salut!" + extra + " Cu ce te pot ajuta?";
        }

        // ── Ajutor / help ─────────────────────────────────────────────────────
        if (has(msg, "ajutor","help","ce stii","ce știi","ce poti","ce poți","optiuni","opțiuni","comenzi")) {
            return "🤖 Pot să-ți spun despre:\n"
                + "• 📋 Task-uri  → \"ce task-uri am?\"\n"
                + "• 🔁 Habits   → \"ce habits am azi?\"\n"
                + "• 😴 Somn     → \"cât am dormit?\"\n"
                + "• 🍅 Pomodoro → \"câte sesiuni azi?\"\n"
                + "• 📊 Progres  → \"cum sunt azi?\"\n"
                + "• 📅 Azi      → \"ce zi e azi?\"\n\n"
                + "Întreabă-mă orice!";
        }

        // ── Tasks ─────────────────────────────────────────────────────────────
        if (has(msg, "task","de facut","de făcut","rezolv","rezolva","todo","ce am","ce mai am")) {
            List<Task> all   = taskRepository.findByUserId(userId);
            List<Task> todos = all.stream().filter(t -> "TODO".equals(t.getStatus())).toList();
            long done        = all.stream().filter(t -> "DONE".equals(t.getStatus())).count();

            if (todos.isEmpty())
                return "🎉 Felicitări! Nu ai niciun task rămas. Poți adăuga unele noi din dashboard.";

            StringBuilder sb = new StringBuilder();
            sb.append("📋 Ai ").append(todos.size())
              .append(" task").append(todos.size() == 1 ? "" : "-uri").append(" de rezolvat");
            if (done > 0) sb.append(" (").append(done).append(" finalizate)");
            sb.append(":\n");
            todos.stream().limit(6).forEach(t ->
                sb.append("• ").append(t.getTitle())
                  .append(" [").append(t.getType()).append("]\n"));
            if (todos.size() > 6) sb.append("...și ").append(todos.size() - 6).append(" altele.");
            return sb.toString().trim();
        }

        // ── Habits ────────────────────────────────────────────────────────────
        if (has(msg, "habit","obicei","bif","repetat","bifat")) {
            List<Habit> habits = habitRepository.findByUserId(userId);
            if (habits.isEmpty())
                return "Nu ai niciun habit setat. Mergi în secțiunea Habits din dashboard să adaugi!";

            List<Long>     ids      = habits.stream().map(Habit::getId).collect(Collectors.toList());
            List<HabitLog> todayLog = habitLogRepository
                .findByHabitIdInAndDateCompletedBetween(ids, today, today);

            long doneCnt  = todayLog.size();
            long totalCnt = habits.size();

            if (doneCnt == totalCnt)
                return "✅ Ai bifat toate " + totalCnt + " habit-urile de azi! Bravo!";

            Set<Long> doneIds = todayLog.stream().map(HabitLog::getHabitId).collect(Collectors.toSet());
            List<String> left = habits.stream()
                .filter(h -> !doneIds.contains(h.getId()))
                .map(Habit::getName).toList();

            StringBuilder sb = new StringBuilder();
            sb.append("🔁 Ai bifat ").append(doneCnt).append(" din ").append(totalCnt).append(" habits azi.\n");
            sb.append("Rămase:\n");
            left.stream().limit(5).forEach(n -> sb.append("• ").append(n).append("\n"));
            return sb.toString().trim();
        }

        // ── Somn ──────────────────────────────────────────────────────────────
        if (has(msg, "somn","dormit","sleep","culcat","trezit","ore de somn","odihn")) {
            List<SleepLog> logs = sleepLogRepository.findByUserIdOrderByLogDateDesc(userId);
            if (logs.isEmpty())
                return "😴 Nu am date de somn. Loghează prima sesiune în tab-ul Sleep!";

            List<SleepLog> last7 = logs.stream().limit(7).toList();
            OptionalDouble avgOpt = last7.stream()
                .filter(s -> s.getBedtime() != null && s.getWakeUpTime() != null)
                .mapToDouble(s -> Duration.between(s.getBedtime(), s.getWakeUpTime()).toMinutes() / 60.0)
                .average();
            double avg = avgOpt.orElse(0);

            SleepLog last = logs.get(0);
            String lastInfo = "";
            if (last.getBedtime() != null && last.getWakeUpTime() != null) {
                double lh = Duration.between(last.getBedtime(), last.getWakeUpTime()).toMinutes() / 60.0;
                lastInfo = String.format(" Ultima noapte: %.1fh.", lh);
            }
            String verdict = avg >= 7.5 ? "Excelent! 🌟"
                           : avg >= 6   ? "Acceptabil, dar poți face mai bine. 💪"
                                        : "Cam puțin... încearcă să dormi mai mult! 😴";

            return String.format("😴 Media ultimelor %d nopți: %.1fh.%s %s",
                last7.size(), avg, lastInfo, verdict);
        }

        // ── Pomodoro ──────────────────────────────────────────────────────────
        if (has(msg, "pomodoro","focus","sesiune","timer","concentr","minut")) {
            LocalDateTime sod = today.atStartOfDay();
            LocalDateTime eod = today.atTime(LocalTime.MAX);
            List<PomodoroSession> todaySess = pomodoroRepository
                .findByUserIdAndStartTimeBetween(userId, sod, eod);
            List<PomodoroSession> all = pomodoroRepository
                .findByUserIdOrderByStartTimeDesc(userId);

            long todayDone   = todaySess.stream().filter(PomodoroSession::isWasCompleted).count();
            int  todayMins   = todaySess.stream().filter(PomodoroSession::isWasCompleted)
                                    .mapToInt(PomodoroSession::getDurationMinutes).sum();
            long totalDone   = all.stream().filter(PomodoroSession::isWasCompleted).count();
            int  totalMins   = all.stream().filter(PomodoroSession::isWasCompleted)
                                    .mapToInt(PomodoroSession::getDurationMinutes).sum();

            if (todayDone == 0)
                return String.format("⏱️ Nicio sesiune Pomodoro azi. Total all-time: %d sesiuni (%dh %dm). Hai să pornim una?",
                    totalDone, totalMins / 60, totalMins % 60);

            return String.format("🍅 Azi: %d sesiuni · %d min focus.\nTotal all-time: %d sesiuni · %dh %dm! 💪",
                todayDone, todayMins, totalDone, totalMins / 60, totalMins % 60);
        }

        // ── Productivitate / cum sunt ─────────────────────────────────────────
        if (has(msg, "productiv","cum sunt","cum merg","progres","scor","azi","ziua")) {
            List<Task>   tasks  = taskRepository.findByUserId(userId);
            List<Habit>  habits = habitRepository.findByUserId(userId);
            List<Long>   hids   = habits.stream().map(Habit::getId).collect(Collectors.toList());
            List<HabitLog> hl   = hids.isEmpty() ? List.of()
                : habitLogRepository.findByHabitIdInAndDateCompletedBetween(hids, today, today);

            LocalDateTime sod = today.atStartOfDay();
            LocalDateTime eod = today.atTime(LocalTime.MAX);
            List<PomodoroSession> pomo = pomodoroRepository
                .findByUserIdAndStartTimeBetween(userId, sod, eod);

            long tasksDone  = tasks.stream()
                .filter(t -> "DONE".equals(t.getStatus())
                    && t.getCompletedAt() != null
                    && t.getCompletedAt().toLocalDate().equals(today)).count();
            long habDone    = hl.size();
            long habTotal   = habits.size();
            long pomoDone   = pomo.stream().filter(PomodoroSession::isWasCompleted).count();
            int  pomoMins   = pomo.stream().filter(PomodoroSession::isWasCompleted)
                                  .mapToInt(PomodoroSession::getDurationMinutes).sum();

            String tEmoji = tasksDone >= 3 ? "🔥" : tasksDone > 0 ? "👍" : "💤";
            String hEmoji = habTotal > 0 && habDone == habTotal ? "✅" : habDone > 0 ? "🔄" : "⭕";
            String pEmoji = pomoDone >= 3 ? "🏆" : pomoDone > 0 ? "⏱️" : "💤";

            return String.format("📊 Ziua ta până acum:\n"
                + "%s %d task-uri finalizate\n"
                + "%s %d/%d habits bifate\n"
                + "%s %d sesiuni Pomodoro (%d min)\n\n"
                + "%s",
                tEmoji, tasksDone,
                hEmoji, habDone, habTotal,
                pEmoji, pomoDone, pomoMins,
                tasksDone + habDone + pomoDone > 0 ? "Continuă tot așa! 💪" : "Hai să începem ziua! 🚀");
        }

        // ── Data ─────────────────────────────────────────────────────────────
        if (has(msg, "data","dată","calendar","ce zi","ziua")) {
            DateTimeFormatter fmt = DateTimeFormatter
                .ofPattern("EEEE, d MMMM yyyy", new Locale("ro", "RO"));
            return "📅 Azi este " + today.format(fmt) + ".";
        }

        // ── Fallback ──────────────────────────────────────────────────────────
        return "🤔 Nu am înțeles exact. Încearcă să mă întrebi despre task-uri, habits, somn sau Pomodoro!\nScrie \"ajutor\" pentru a vedea ce pot face.";
    }

    // ════════════════════════════════════════════════════════════════════════
    // PROACTIVE MESSAGE GENERATOR
    // ════════════════════════════════════════════════════════════════════════

    private String generateProactive(Long userId) {
        LocalDate today = LocalDate.now();

        // 1. Task-uri de rezolvat
        List<Task> todos = taskRepository.findByUserId(userId).stream()
            .filter(t -> "TODO".equals(t.getStatus())).toList();
        if (!todos.isEmpty()) {
            Task pick = todos.get(RNG.nextInt(todos.size()));
            if (todos.size() == 1)
                return "📋 Ai un task de rezolvat: \"" + pick.getTitle() + "\". Hai să-l bifezi!";
            return "📋 Ai " + todos.size() + " task-uri de rezolvat! "
                + "Ce-ar fi să rezolvi \"" + pick.getTitle() + "\" acum?";
        }

        // 2. Habits de bifat azi
        List<Habit> habits = habitRepository.findByUserId(userId);
        if (!habits.isEmpty()) {
            List<Long> ids = habits.stream().map(Habit::getId).collect(Collectors.toList());
            List<HabitLog> todayLog = habitLogRepository
                .findByHabitIdInAndDateCompletedBetween(ids, today, today);
            if (todayLog.isEmpty())
                return "🔁 Nu ai bifat niciun habit azi! Ai " + habits.size() + " de completat.";
            if (todayLog.size() < habits.size())
                return "🔁 Ai bifat " + todayLog.size() + " din " + habits.size()
                    + " habits azi. Mai " + (habits.size() - todayLog.size()) + " de mers!";
        }

        // 3. Niciun Pomodoro azi
        LocalDateTime sod = today.atStartOfDay();
        LocalDateTime eod = today.atTime(LocalTime.MAX);
        List<PomodoroSession> todayPomo = pomodoroRepository
            .findByUserIdAndStartTimeBetween(userId, sod, eod);
        if (todayPomo.isEmpty())
            return "⏱️ N-ai nicio sesiune de focus azi. Ce zici de un Pomodoro de 25 de minute?";

        // 4. Somn insuficient
        List<SleepLog> sleepLogs = sleepLogRepository.findByUserIdOrderByLogDateDesc(userId);
        if (!sleepLogs.isEmpty()) {
            OptionalDouble avg = sleepLogs.stream().limit(3)
                .filter(s -> s.getBedtime() != null && s.getWakeUpTime() != null)
                .mapToDouble(s -> Duration.between(s.getBedtime(), s.getWakeUpTime()).toMinutes() / 60.0)
                .average();
            if (avg.isPresent() && avg.getAsDouble() < 6.5)
                return String.format("😴 Ai dormit în medie %.1fh în ultimele nopți. "
                    + "Somnul afectează productivitatea — încearcă să dormi mai mult!", avg.getAsDouble());
        }

        // 5. Totul bine — mesaj motivațional random
        String[] msgs = {
            "🌟 Toate task-urile sunt la zi! Zi productivă! Ce adaugi nou?",
            "💪 Ești pe drumul cel bun! Continuă tot așa!",
            "🎯 Ai bifat tot ce trebuia. Impresionant!",
            "✨ Nu ai task-uri restante. Cum îți mai poți îmbunătăți ziua?",
            "🚀 Productivitate maximă! Ce urmează?",
        };
        return msgs[RNG.nextInt(msgs.length)];
    }

    // ─── Utilitare ────────────────────────────────────────────────────────────

    private boolean has(String text, String... keywords) {
        for (String kw : keywords) if (text.contains(kw)) return true;
        return false;
    }
}
