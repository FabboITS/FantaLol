package com.fantalol.backend.config;

import com.fantalol.backend.security.CustomUserDetailsService;
import com.fantalol.backend.security.JwtAuthFilter;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.List;

/**
 * Configura Spring Security in modalità stateless (JWT), definendo:
 * <ul>
 *     <li>endpoint pubblici (registrazione, login, consultazione team/player LEC)</li>
 *     <li>endpoint autenticati (gestione leghe, rose, formazioni)</li>
 *     <li>endpoint riservati al ruolo ADMIN (inserimento statistiche, gestione anagrafica LEC)</li>
 * </ul>
 */
@Configuration
@EnableMethodSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final CustomUserDetailsService userDetailsService;
    private final JwtAuthFilter jwtAuthFilter;

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public DaoAuthenticationProvider authenticationProvider() {
        DaoAuthenticationProvider provider = new DaoAuthenticationProvider();
        provider.setUserDetailsService(userDetailsService);
        provider.setPasswordEncoder(passwordEncoder());
        return provider;
    }

    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration config) throws Exception {
        return config.getAuthenticationManager();
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .exceptionHandling(exceptions -> exceptions
                        .authenticationEntryPoint((request, response, exception) ->
                                response.sendError(HttpStatus.UNAUTHORIZED.value(), "Unauthorized")))
                .cors(cors -> cors.configurationSource(corsConfigurationSource()))
                .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        // Frontend statico servito direttamente da Spring Boot
                        .requestMatchers("/", "/index.html", "/css/**", "/js/**", "/assets/**",
                                "/Player_immage/**", "/favicon.ico", "/favicon.svg").permitAll()

                        // Endpoint pubblici: autenticazione e documentazione
                        .requestMatchers("/api/auth/**").permitAll()
                        .requestMatchers("/swagger-ui/**", "/v3/api-docs/**", "/swagger-ui.html").permitAll()
                        .requestMatchers("/actuator/health").permitAll()

                        // Consultazione pubblica dell'anagrafica LEC (team e player) e delle giornate
                        .requestMatchers(HttpMethod.GET, "/api/teams/**", "/api/players/**", "/api/matchdays/**").permitAll()

                        // Scrittura sull'anagrafica LEC: solo ADMIN
                        .requestMatchers(HttpMethod.POST, "/api/teams/**", "/api/players/**").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.PUT, "/api/teams/**", "/api/players/**").hasRole("ADMIN")
                        .requestMatchers(HttpMethod.DELETE, "/api/teams/**", "/api/players/**").hasRole("ADMIN")

                        // Creazione giornate, inserimento statistiche e chiusura giornata: solo ADMIN
                        .requestMatchers(HttpMethod.POST, "/api/matchdays/**").authenticated()

                        // Directory degli username registrati: solo ADMIN
                        .requestMatchers(HttpMethod.GET, "/api/users").hasRole("ADMIN")

                        // Tutto il resto richiede autenticazione (leghe, rose, formazioni, profilo)
                        .anyRequest().authenticated()
                )
                .authenticationProvider(authenticationProvider())
                .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOriginPatterns(List.of("*"));
        configuration.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(List.of("*"));
        configuration.setAllowCredentials(true);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }
}
