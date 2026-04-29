package com.licenta.repository;

import com.licenta.model.PomodoroSession;
import org.springframework.data.jpa.repository.JpaRepository;
import java.time.LocalDateTime;
import java.util.List;

public interface PomodoroRepository extends JpaRepository<PomodoroSession, Long> {
    List<PomodoroSession> findByUserIdOrderByStartTimeDesc(Long userId);
    List<PomodoroSession> findByUserIdAndStartTimeBetween(Long userId, LocalDateTime start, LocalDateTime end);
}
