package com.licenta.model;

import jakarta.persistence.*;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "tasks")
public class Task {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Long userId;
    private String title;
    private String type;   // CLASSIC, QUICK, RADAR
    private String status; // TODO, DONE
    private LocalDate dueDate;
    private LocalDateTime completedAt;
    private double xPosition;
    private double yPosition;

    @ManyToOne
    @JoinColumn(name = "project_id")
    private Project project;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getType() { return type; }
    public void setType(String type) { this.type = type; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public LocalDate getDueDate() { return dueDate; }
    public void setDueDate(LocalDate dueDate) { this.dueDate = dueDate; }
    public LocalDateTime getCompletedAt() { return completedAt; }
    public void setCompletedAt(LocalDateTime completedAt) { this.completedAt = completedAt; }
    public double getxPosition() { return xPosition; }
    public void setxPosition(double xPosition) { this.xPosition = xPosition; }
    public double getyPosition() { return yPosition; }
    public void setyPosition(double yPosition) { this.yPosition = yPosition; }
    public Project getProject() { return project; }
    public void setProject(Project project) { this.project = project; }
}
