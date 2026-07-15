# Frontend Port 8080 and Favicon Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the separate frontend into Spring Boot, serve it on port 8080, serve a favicon successfully, and return 404 for missing static resources.

**Architecture:** Maven copies `fantalol-frontend` into the build output's `static` directory, allowing Spring Boot's standard resource handler to serve the frontend and API from one process. An SVG favicon lives with the frontend sources, while `GlobalExceptionHandler` maps Spring MVC's missing-resource exception to 404.

**Tech Stack:** Java 17, Spring Boot 3.3.4, Spring MVC, Spring Security, Maven, JUnit 5, MockMvc, SVG

## Global Constraints

- Keep frontend source in `fantalol-frontend`.
- Serve frontend and backend through Spring Boot on port 8080.
- Do not introduce a second frontend server or change API and authentication behavior.
- Do not perform Git operations.

---

### Task 1: Static Resource Regression Tests

**Files:**
- Create: `fantalol-backend/src/test/java/com/fantalol/backend/common/StaticResourceIntegrationTest.java`

**Interfaces:**
- Consumes: Spring MVC static-resource handling and `GlobalExceptionHandler`.
- Produces: Regression coverage for `GET /favicon.svg` and `GET /favicon.ico`.

- [ ] **Step 1: Write failing integration tests**

Create a Spring Boot `MockMvc` test using the test profile. Assert that `/favicon.svg` returns 200 with `image/svg+xml`, and that the browser's fallback `/favicon.ico` path returns 404 with an `ApiError` body whose `status` is 404 and `path` matches the request.

- [ ] **Step 2: Run tests and verify RED**

Run: `mvn -Dtest=StaticResourceIntegrationTest test`

Expected: `/favicon.svg` fails because the resource is absent, and `/favicon.ico` fails because the generic handler currently returns 500.

### Task 2: Package and Serve the Frontend

**Files:**
- Modify: `fantalol-backend/pom.xml`
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/config/SecurityConfig.java`
- Modify: `fantalol-backend/Dockerfile`
- Modify: `fantalol-backend/docker-compose.yml`
- Create: `fantalol-frontend/favicon.svg`
- Modify: `fantalol-frontend/index.html`

**Interfaces:**
- Consumes: Maven resource copying and Spring Boot's `classpath:/static/` convention.
- Produces: Classpath resources `static/index.html`, `static/favicon.svg`, `static/css/**`, and `static/js/**`.

- [ ] **Step 1: Add the frontend Maven resource**

Add a `<resources>` section under `<build>` that preserves `src/main/resources` and copies `../fantalol-frontend` into `${project.build.outputDirectory}/static` during `process-resources`.

Update the Docker build context to the repository root and copy both `fantalol-backend` and `fantalol-frontend` into the Maven build stage, preserving the same sibling layout used by the Maven resource configuration.

- [ ] **Step 2: Add and reference the favicon**

Create a compact branded SVG with a square view box and add `<link rel="icon" href="/favicon.svg" type="image/svg+xml">` to the document head.

- [ ] **Step 3: Permit the favicon request**

Add `/favicon.svg` to the existing public static-resource matchers in `SecurityConfig` so browsers can retrieve it without a JWT.

- [ ] **Step 4: Run the focused test**

Run: `mvn -Dtest=StaticResourceIntegrationTest test`

Expected: the SVG favicon assertion passes; the ICO fallback assertion still reports 500 until Task 3.

### Task 3: Correct Missing-Resource Status

**Files:**
- Modify: `fantalol-backend/src/main/java/com/fantalol/backend/common/GlobalExceptionHandler.java`

**Interfaces:**
- Consumes: `org.springframework.web.servlet.resource.NoResourceFoundException`.
- Produces: `ResponseEntity<ApiError> handleNoResourceFound(NoResourceFoundException, HttpServletRequest)` with HTTP 404.

- [ ] **Step 1: Add the narrow exception mapping**

Import `NoResourceFoundException` and add an `@ExceptionHandler` method that returns `ApiError.of(404, "Not Found", "Risorsa non trovata", req.getRequestURI())`.

- [ ] **Step 2: Run focused tests and verify GREEN**

Run: `mvn -Dtest=StaticResourceIntegrationTest test`

Expected: both tests pass.

### Task 4: Full Verification

**Files:**
- Verify only; no additional files.

**Interfaces:**
- Consumes: completed frontend packaging and error mapping.
- Produces: evidence that the change passes all tests and is present in the packaged JAR.

- [ ] **Step 1: Run all tests**

Run: `mvn test`

Expected: build success with all tests passing.

- [ ] **Step 2: Package and inspect the JAR**

Run: `mvn package -DskipTests`, followed by `jar tf target/fantalol-backend.jar` filtered for `BOOT-INF/classes/static/index.html` and `BOOT-INF/classes/static/favicon.svg`.

Expected: both resources are present.

- [ ] **Step 3: Check the project diff**

Run: `git diff --check`

Expected: no whitespace errors. Do not stage or commit files.
