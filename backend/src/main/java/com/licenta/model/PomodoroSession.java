package com.licenta.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "pomodoro_sessions")
public class PomodoroSession {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long userId;
    private Long taskId;
    private int durationMinutes;
    private boolean wasCompleted;
    private LocalDateTime startTime;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }
    public Long getTaskId() { return taskId; }
    public void setTaskId(Long taskId) { this.taskId = taskId; }
    public int getDurationMinutes() { return durationMinutes; }
    public void setDurationMinutes(int durationMinutes) { this.durationMinutes = durationMinutes; }
    public boolean isWasCompleted() { return wasCompleted; }
    public void setWasCompleted(boolean wasCompleted) { this.wasCompleted = wasCompleted; }
    public LocalDateTime getStartTime() { return startTime; }
    public void setStartTime(LocalDateTime startTime) { this.startTime = startTime; }
}
