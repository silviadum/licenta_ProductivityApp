package com.licenta.controller;

import com.licenta.model.Habit;
import com.licenta.model.HabitLog;
import com.licenta.repository.HabitLogRepository;
import com.licenta.repository.HabitRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/habits")
@CrossOrigin(origins = "*")
public class HabitController {

    @Autowired
    private HabitRepository habitRepository;

    @Autowired
    private HabitLogRepository habitLogRepository;

    @GetMapping("/all")
    public List<Habit> getAll() {
        return habitRepository.findAll();
    }

    @GetMapping("/user/{userId}")
    public List<Habit> getByUser(@PathVariable Long userId) {
        return habitRepository.findByUserId(userId);
    }

    @PostMapping("/add")
    public Habit addHabit(@RequestBody Habit habit) {
        habit.setActive(true);
        return habitRepository.save(habit);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<?> deleteHabit(@PathVariable Long id) {
        habitRepository.deleteById(id);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/{habitId}/log")
    public ResponseEntity<?> logHabit(@PathVariable Long habitId, @RequestBody Map<String, String> body) {
        String dateStr = body.get("date");
        LocalDate logDate = (dateStr != null && !dateStr.isEmpty()) ? LocalDate.parse(dateStr) : LocalDate.now();

        Optional<HabitLog> existing = habitLogRepository.findByHabitIdAndDateCompleted(habitId, logDate);
        if (existing.isPresent()) {
            habitLogRepository.delete(existing.get());
            return ResponseEntity.ok(Map.of("logged", false));
        } else {
            HabitLog log = new HabitLog();
            log.setHabitId(habitId);
            log.setDateCompleted(logDate);
            habitLogRepository.save(log);
            return ResponseEntity.ok(Map.of("logged", true));
        }
    }

    @GetMapping("/user/{userId}/logs")
    public List<HabitLog> getAllUserLogs(@PathVariable Long userId) {
        List<Habit> habits = habitRepository.findByUserId(userId);
        List<Long> habitIds = habits.stream().map(Habit::getId).collect(Collectors.toList());
        if (habitIds.isEmpty()) return List.of();
        return habitLogRepository.findByHabitIdIn(habitIds);
    }

    @GetMapping("/user/{userId}/logs/week")
    public List<HabitLog> getUserWeekLogs(@PathVariable Long userId) {
        List<Habit> habits = habitRepository.findByUserId(userId);
        List<Long> habitIds = habits.stream().map(Habit::getId).collect(Collectors.toList());
        if (habitIds.isEmpty()) return List.of();

        LocalDate today = LocalDate.now();
        LocalDate monday = today.with(DayOfWeek.MONDAY);
        LocalDate sunday = monday.plusDays(6);

        return habitLogRepository.findByHabitIdInAndDateCompletedBetween(habitIds, monday, sunday);
    }
}
