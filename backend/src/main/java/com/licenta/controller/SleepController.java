package com.licenta.controller;

import com.licenta.model.SleepLog;
import com.licenta.repository.SleepLogRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/sleep")
@CrossOrigin(origins = "*")
public class SleepController {

    @Autowired
    private SleepLogRepository sleepLogRepository;

    @GetMapping("/user/{userId}")
    public List<SleepLog> getByUser(@PathVariable Long userId) {
        return sleepLogRepository.findByUserIdOrderByLogDateDesc(userId);
    }

    @PostMapping("/add")
    public ResponseEntity<?> add(@RequestBody SleepLog sleepLog) {
        // If a log for this date already exists, update it
        Optional<SleepLog> existing = sleepLogRepository.findByUserIdAndLogDate(
                sleepLog.getUserId(), sleepLog.getLogDate());
        if (existing.isPresent()) {
            SleepLog e = existing.get();
            e.setBedtime(sleepLog.getBedtime());
            e.setWakeUpTime(sleepLog.getWakeUpTime());
            e.setQualityScore(sleepLog.getQualityScore());
            return ResponseEntity.ok(sleepLogRepository.save(e));
        }
        return ResponseEntity.ok(sleepLogRepository.save(sleepLog));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<?> delete(@PathVariable Long id) {
        sleepLogRepository.deleteById(id);
        return ResponseEntity.ok().build();
    }
}
