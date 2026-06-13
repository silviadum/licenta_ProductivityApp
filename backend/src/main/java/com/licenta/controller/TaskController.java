package com.licenta.controller;

import com.licenta.model.Task;
import com.licenta.repository.TaskRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/tasks")
@CrossOrigin(origins = "*")
public class TaskController {

    @Autowired
    private TaskRepository taskRepository;

    @GetMapping("/all")
    public List<Task> getAll() {
        return taskRepository.findAll();
    }

    @GetMapping("/user/{userId}")
    public List<Task> getByUser(@PathVariable Long userId) {
        return taskRepository.findByUserId(userId);
    }

    @GetMapping("/user/{userId}/type/{type}")
    public List<Task> getByUserAndType(@PathVariable Long userId, @PathVariable String type) {
        return taskRepository.findByUserIdAndType(userId, type.toUpperCase());
    }

    @PostMapping("/add")
    public Task addTask(@RequestBody Task task) {
        if (task.getStatus() == null) task.setStatus("TODO");
        if (task.getType() == null) task.setType("CLASSIC");
        if (task.getxPosition() == 0) task.setxPosition(Math.random() * 80 + 10);
        if (task.getyPosition() == 0) task.setyPosition(Math.random() * 80 + 10);
        if (task.getSortOrder() == null) {
            // pune-l la coadă pentru tipul lui
            int maxOrder = taskRepository.findByUserIdAndType(task.getUserId(), task.getType()).stream()
                    .map(Task::getSortOrder).filter(java.util.Objects::nonNull)
                    .mapToInt(Integer::intValue).max().orElse(-1);
            task.setSortOrder(maxOrder + 1);
        }
        return taskRepository.save(task);
    }

    @PutMapping("/{id}/toggle")
    public ResponseEntity<?> toggleTask(@PathVariable Long id) {
        Optional<Task> opt = taskRepository.findById(id);
        if (opt.isEmpty()) return ResponseEntity.notFound().build();
        Task task = opt.get();
        boolean wasDone = "DONE".equals(task.getStatus());
        task.setStatus(wasDone ? "TODO" : "DONE");
        task.setCompletedAt(wasDone ? null : LocalDateTime.now());
        return ResponseEntity.ok(taskRepository.save(task));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<?> deleteTask(@PathVariable Long id) {
        taskRepository.deleteById(id);
        return ResponseEntity.ok().build();
    }

    /**
     * Reordonare: primește lista de id-uri în noua ordine.
     * Body: { "ids": [3, 1, 7, 4] }
     */
    @PutMapping("/reorder")
    public ResponseEntity<?> reorderTasks(@RequestBody Map<String, List<Long>> body) {
        List<Long> ids = body.get("ids");
        if (ids == null) return ResponseEntity.badRequest().build();
        for (int i = 0; i < ids.size(); i++) {
            Long id = ids.get(i);
            taskRepository.findById(id).ifPresent(t -> {
                t.setSortOrder(ids.indexOf(t.getId()));
                taskRepository.save(t);
            });
        }
        return ResponseEntity.ok().build();
    }
}
