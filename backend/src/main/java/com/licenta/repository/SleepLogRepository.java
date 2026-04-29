package com.licenta.repository;

import com.licenta.model.SleepLog;
import org.springframework.data.jpa.repository.JpaRepository;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

public interface SleepLogRepository extends JpaRepository<SleepLog, Long> {
    List<SleepLog> findByUserIdOrderByLogDateDesc(Long userId);
    Optional<SleepLog> findByUserIdAndLogDate(Long userId, LocalDate logDate);
}
