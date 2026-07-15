# Frontend on Port 8080 and Favicon Error Fix

## Goal

Serve the frontend and backend from the Spring Boot application on port 8080 while keeping the frontend source in the top-level `fantalol-frontend` directory. A request for the site favicon must succeed, and other missing static resources must return HTTP 404 rather than HTTP 500.

## Architecture

Maven will treat `fantalol-frontend` as an additional resource directory and copy its contents beneath `static/` in the application output. Spring Boot's standard static-resource handling will then serve `index.html`, CSS, JavaScript, and the favicon from the same origin as the API. This avoids a second web server and works in both the executable JAR and Docker image.

The frontend will explicitly reference `/favicon.svg`. The SVG will be stored with the other frontend source files and packaged by Maven.

## Error Handling

Spring MVC raises `NoResourceFoundException` when a requested static asset does not exist. The global REST exception handler will map that exception to HTTP 404. Its existing generic handler will remain responsible for unexpected failures and continue returning HTTP 500.

## Testing

An integration test will first reproduce the current packaging failure by requesting the frontend favicon and expecting HTTP 200 with an image content type. A second test will request an unknown static resource and expect HTTP 404. After the tests fail for the expected reasons, the Maven resource configuration, favicon, HTML reference, and exception mapping will be implemented.

Verification will include the focused integration tests, the complete Maven test suite, inspection of the packaged JAR contents, and an HTTP check against the running packaged application when the local test environment permits it.

## Scope

This change will not introduce a separate frontend development server, change API routes, redesign the page, or alter authentication behavior.
