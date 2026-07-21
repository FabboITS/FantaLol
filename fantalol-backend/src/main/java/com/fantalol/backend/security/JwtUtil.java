package com.fantalol.backend.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.util.Date;
import java.util.function.Function;

/**
 * Componente responsabile della generazione e validazione dei token JWT
 * usati per l'autenticazione stateless degli endpoint REST.
 */
@Component
public class JwtUtil {

    private final SecretKey secretKey;
    private final long expirationMs;

    public JwtUtil(
            @Value("${fantalol.jwt.secret}") String secret,
            @Value("${fantalol.jwt.expiration-ms}") long expirationMs
    ) {
        if (secret == null || secret.isBlank()) {
            throw new IllegalArgumentException(
                    "La variabile JWT_SECRET non è configurata"
            );
        }

        byte[] keyBytes;

        try {
            keyBytes = Decoders.BASE64.decode(secret.trim());
        } catch (IllegalArgumentException exception) {
            throw new IllegalArgumentException(
                    "JWT_SECRET deve essere una stringa Base64 valida",
                    exception
            );
        }

        if (keyBytes.length < 32) {
            throw new IllegalArgumentException(
                    "JWT_SECRET deve contenere almeno 32 byte dopo la decodifica Base64"
            );
        }

        this.secretKey = Keys.hmacShaKeyFor(keyBytes);
        this.expirationMs = expirationMs;
    }

    public String generateToken(UserDetails userDetails) {
        Date now = new Date();
        Date expiry = new Date(now.getTime() + expirationMs);

        return Jwts.builder()
                .subject(userDetails.getUsername())
                .claim(
                        "authorities",
                        userDetails.getAuthorities()
                                .stream()
                                .map(Object::toString)
                                .toList()
                )
                .issuedAt(now)
                .expiration(expiry)
                .signWith(secretKey)
                .compact();
    }

    public String extractUsername(String token) {
        return extractClaim(token, Claims::getSubject);
    }

    public boolean isTokenValid(String token, UserDetails userDetails) {
        String username = extractUsername(token);

        return username.equals(userDetails.getUsername())
                && !isTokenExpired(token);
    }

    private boolean isTokenExpired(String token) {
        return extractClaim(token, Claims::getExpiration)
                .before(new Date());
    }

    private <T> T extractClaim(
            String token,
            Function<Claims, T> claimsResolver
    ) {
        Claims claims = Jwts.parser()
                .verifyWith(secretKey)
                .build()
                .parseSignedClaims(token)
                .getPayload();

        return claimsResolver.apply(claims);
    }
}
