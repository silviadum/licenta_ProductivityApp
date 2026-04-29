package com.licenta.model;

import jakarta.persistence.*;
import java.time.LocalDate;

@Entity
@Table(name = "habit_logs")
public class HabitLog {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long habitId;
    private LocalDate dateCompleted;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getHabitId() { return habitId; }
    public void setHabitId(Long habitId) { this.habitId = habitId; }
    public LocalDate getDateCompleted() { return dateCompleted; }
    public void setDateCompleted(LocalDate dateCompleted) { this.dateCompleted = dateCompleted; }
}
