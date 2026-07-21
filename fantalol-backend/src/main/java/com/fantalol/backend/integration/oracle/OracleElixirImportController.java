package com.fantalol.backend.integration.oracle;

import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/admin/oracle-elixir")
@RequiredArgsConstructor
public class OracleElixirImportController {
    private final OracleElixirCsvImporter importer;

    @PostMapping(value = "/matchdays/{matchdayId}/import", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public OracleImportResult importMatchday(
            Authentication authentication,
            @PathVariable Long matchdayId,
            @RequestPart("file") MultipartFile file,
            @RequestParam(defaultValue = "LEC") String league,
            @RequestParam String split
    ) {
        if (authentication == null) {
            throw new IllegalStateException("Authentication is required");
        }
        return importer.importCsv(matchdayId, file, league, split);
    }
}
