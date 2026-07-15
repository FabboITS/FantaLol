# ---------- STAGE 1: build ----------
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app

# Copiamo prima il pom.xml per sfruttare la cache dei layer Docker sulle dipendenze
COPY pom.xml .
RUN mvn -B dependency:go-offline

COPY src ./src
RUN mvn -B clean package -DskipTests

# ---------- STAGE 2: runtime ----------
FROM eclipse-temurin:17-jre-jammy
WORKDIR /app

RUN addgroup --system fantalol && adduser --system --ingroup fantalol fantalol
COPY --from=build /app/target/fantalol-backend.jar app.jar
RUN chown fantalol:fantalol app.jar
USER fantalol

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
