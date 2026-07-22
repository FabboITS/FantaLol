# Technical Report Refresh Design

## Goal

Update `fantalol-backend/relazione/Relazione_Tecnica_FantaLoL.docx` so it accurately documents the application as it exists on July 22, 2026, while preserving the report's Italian language, structure, cover, and visual style.

## Source of Truth

The implementation, tests, root README, integration documentation, Maven configuration, frontend files, and Docker configuration are authoritative. Existing report statements that conflict with those sources will be replaced rather than retained as historical notes.

## Content Changes

The refreshed report will document the static HTML/CSS/JavaScript frontend bundled into the Spring Boot artifact; role-based league visibility and deletion; the global administrator user directory; timed auction sessions and bids; participant-dependent roster limits; manual and automatic formations; matchday lifecycle and postponed matches; arithmetic-mean team scoring; PandaScore and Oracle's Elixir integrations; general standings; and the expanded automated test suite.

Outdated claims will be corrected, including the previous eight-player roster limit, direct-offer-only auction description, base-vote/MVP/captain scoring formula, and future-work entries for features that are already implemented.

## Document Editing Strategy

The original DOCX will first be copied to a timestamp-free `.backup.docx` file in the same directory. The main document will then be updated in place. Existing paragraph and heading styles will be reused. The report will remain in Italian, and no Git command will be executed.

## Validation

The resulting DOCX must remain a valid ZIP-based Office Open XML package. Its text will be extracted after editing and checked for the new architecture, auction, roster, scoring, integration, administration, and testing descriptions, as well as the absence of the main obsolete claims. If LibreOffice is available, it will also be used in headless mode to confirm the document opens and can be rendered successfully.
