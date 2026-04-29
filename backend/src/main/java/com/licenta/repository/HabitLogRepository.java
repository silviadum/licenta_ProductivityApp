package com.licenta.repository;

import com.licenta.model.HabitLog;
import org.springframework.data.jpa.repository.JpaRepository;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

public interface HabitLogRepository extends JpaRepository<HabitLog, Long> {
    List<HabitLog> findByHabitIdIn(List<Long> habitIds);
    List<HabitLog> findByHabitIdInAndDateCompletedBetween(List<Long> habitIds, LocalDate start, LocalDate end);
    Optional<HabitLog> findByHabitIdAndDateCompleted(Long habitId, LocalDate dateCompleted);
    void deleteByHabitIdIn(List<Long> habitIds);
}
