package com.licenta.controller;

import com.licenta.model.User;
import com.licenta.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/users")
@CrossOrigin(origins = "*")
public class UserController {

    @Autowired
    private UserRepository userRepository;

    @PutMapping("/{id}")
    public ResponseEntity<?> updateUser(@PathVariable Long id, @RequestBody Map<String, String> body) {
        Optional<User> opt = userRepository.findById(id);
        if (opt.isEmpty()) return ResponseEntity.notFound().build();
        User u = opt.get();
        if (body.containsKey("username") && !body.get("username").isBlank())
            u.setUsername(body.get("username"));
        if (body.containsKey("password") && !body.get("password").isBlank())
            u.setPassword(body.get("password"));
        return ResponseEntity.ok(userRepository.save(u));
    }

    @PostMapping("/register")
    public ResponseEntity<?> register(@RequestBody User user) {
        // Verificăm dacă există deja
        if (userRepository.findByEmail(user.getEmail()).isPresent()) {
            return ResponseEntity.status(400).body(Map.of("message", "Email deja existent"));
        }

        userRepository.save(user);

        // Trimitem un JSON clar înapoi, nu doar un string
        return ResponseEntity.ok(Map.of(
                "status", "success",
                "message", "Utilizator creat"
        ));
    }
    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody User user) {
        Optional<User> dbUser = userRepository.findByEmail(user.getEmail());

        if (dbUser.isPresent() && dbUser.get().getPassword().equals(user.getPassword())) {
            return ResponseEntity.ok(Map.of(
                    "status", "success",
                    "message", "Autentificare reușită!",
                    "user", dbUser.get()
            ));
        }
        return ResponseEntity.status(401).body(Map.of("status", "error", "message", "Email sau parolă incorectă"));
    }
}