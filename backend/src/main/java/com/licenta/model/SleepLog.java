package com.licenta.model;

import jakarta.persistence.*;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "sleep_logs")
public class SleepLog {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long userId;
    private LocalDateTime bedtime;
    private LocalDateTime wakeUpTime;
    private Integer qualityScore; // 1..10
    private LocalDate logDate;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }
    public LocalDateTime getBedtime() { return bedtime; }
    public void setBedtime(LocalDateTime bedtime) { this.bedtime = bedtime; }
    public LocalDateTime getWakeUpTime() { return wakeUpTime; }
    public void setWakeUpTime(LocalDateTime wakeUpTime) { this.wakeUpTime = wakeUpTime; }
    public Integer getQualityScore() { return qualityScore; }
    public void setQualityScore(Integer qualityScore) { this.qualityScore = qualityScore; }
    public LocalDate getLogDate() { return logDate; }
    public void setLogDate(LocalDate logDate) { this.logDate = logDate; }
}
