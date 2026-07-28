package com.fantalol.backend.scoring;

import com.fantalol.backend.integration.lec.ProviderSyncState;
import com.fantalol.backend.integration.lec.ProviderSyncStateRepository;
import com.fantalol.backend.integration.oracle.ProviderGame;
import com.fantalol.backend.scoring.dto.CumulativeDataResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class CumulativeDataFreshnessService {

    private final ProviderSyncStateRepository repository;

    @Transactional(readOnly = true)
    public <T> CumulativeDataResponse<T> wrap(List<T> items) {
        ProviderSyncState state = repository.findByProvider(ProviderGame.ORACLES_ELIXIR).orElse(null);
        if (state == null || state.getLastSuccessAt() == null) {
            return new CumulativeDataResponse<>("awaiting-data", null, true, items);
        }
        if ("FAILED".equals(state.getStatus())) {
            return new CumulativeDataResponse<>("stale", state.getLastSuccessAt(), true, items);
        }
        return new CumulativeDataResponse<>("fresh", state.getLastSuccessAt(), false, items);
    }
}
