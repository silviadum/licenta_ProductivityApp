package com.licenta.controller;

import com.licenta.model.User;
import com.licenta.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/users")
@CrossOrigin(origins = "*")
public class UserController {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private BCryptPasswordEncoder encoder;

    // ── Helper: detectează parolele deja hash-uite (BCrypt prefix) ─────────────
    private boolean isBcryptHash(String s) {
        return s != null && (s.startsWith("$2a$") || s.startsWith("$2b$") || s.startsWith("$2y$"));
    }

    @PutMapping("/{id}")
    public ResponseEntity<?> updateUser(@PathVariable Long id, @RequestBody Map<String, String> body) {
        Optional<User> opt = userRepository.findById(id);
        if (opt.isEmpty()) return ResponseEntity.notFound().build();
        User u = opt.get();
        if (body.containsKey("username") && !body.get("username").isBlank())
            u.setUsername(body.get("username"));
        if (body.containsKey("password") && !body.get("password").isBlank())
            u.setPassword(encoder.encode(body.get("password")));
        return ResponseEntity.ok(userRepository.save(u));
    }

    @PostMapping("/register")
    public ResponseEntity<?> register(@RequestBody User user) {
        if (userRepository.findByEmail(user.getEmail()).isPresent()) {
            return ResponseEntity.status(400).body(Map.of("message", "Email deja existent"));
        }
        // hash-uire la înregistrare
        user.setPassword(encoder.encode(user.getPassword()));
        userRepository.save(user);

        return ResponseEntity.ok(Map.of(
                "status", "success",
                "message", "Utilizator creat"
        ));
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody User user) {
        Optional<User> dbUserOpt = userRepository.findByEmail(user.getEmail());
        if (dbUserOpt.isEmpty()) {
            return ResponseEntity.status(401).body(Map.of("status", "error", "message", "Email sau parolă incorectă"));
        }
        User dbUser = dbUserOpt.get();
        String stored = dbUser.getPassword();
        String provided = user.getPassword();

        boolean ok;
        if (isBcryptHash(stored)) {
            ok = encoder.matches(provided, stored);
        } else {
            // Fallback (legacy plaintext): comparăm direct, iar dacă e ok, hash-uim acum.
            ok = stored != null && stored.equals(provided);
            if (ok) {
                dbUser.setPassword(encoder.encode(provided));
                userRepository.save(dbUser);
            }
        }

        if (!ok) {
            return ResponseEntity.status(401).body(Map.of("status", "error", "message", "Email sau parolă incorectă"));
        }

        return ResponseEntity.ok(Map.of(
                "status", "success",
                "message", "Autentificare reușită!",
                "user", dbUser
        ));
    }
}
