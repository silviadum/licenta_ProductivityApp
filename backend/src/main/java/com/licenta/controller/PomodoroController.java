package com.licenta.controller;

import com.licenta.model.PomodoroSession;
import com.licenta.repository.PomodoroRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.List;

@RestController
@RequestMapping("/api/pomodoro")
@CrossOrigin(origins = "*")
public class PomodoroController {

    @Autowired
    private PomodoroRepository pomodoroRepository;

    @PostMapping("/add")
    public PomodoroSession add(@RequestBody PomodoroSession session) {
        if (session.getStartTime() == null) {
            session.setStartTime(LocalDateTime.now());
        }
        return pomodoroRepository.save(session);
    }

    @GetMapping("/user/{userId}")
    public List<PomodoroSession> getByUser(@PathVariable Long userId) {
        return pomodoroRepository.findByUserIdOrderByStartTimeDesc(userId);
    }

    @GetMapping("/user/{userId}/today")
    public List<PomodoroSession> getTodayByUser(@PathVariable Long userId) {
        LocalDateTime startOfDay = LocalDate.now().atStartOfDay();
        LocalDateTime endOfDay = LocalDate.now().atTime(LocalTime.MAX);
        return pomodoroRepository.findByUserIdAndStartTimeBetween(userId, startOfDay, endOfDay);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<?> delete(@PathVariable Long id) {
        pomodoroRepository.deleteById(id);
        return ResponseEntity.ok().build();
    }
}
