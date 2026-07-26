package com.fantalol.backend.scoring;

import com.fantalol.backend.scoring.dto.LecInsightsResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/lec/summer-2026")
@RequiredArgsConstructor
public class LecInsightsController {
    private final LecInsightsService service;

    @GetMapping("/insights")
    public LecInsightsResponse insights() {
        return service.summer2026();
    }
}
