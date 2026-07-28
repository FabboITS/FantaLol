package com.fantalol.backend.integration.lec;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@ActiveProfiles("test")
class ProviderSyncStateTransactionIntegrationTest {
    @Autowired
    private ProviderSyncStateService stateService;
    @Autowired
    private ProviderSyncStateRepository repository;
    @Autowired
    private org.springframework.transaction.PlatformTransactionManager transactionManager;

    @AfterEach
    void cleanUp() {
        repository.deleteAll();
    }

    @Test
    void failureStatusCommitsOutsideARollingBackCallerTransaction() {
        TransactionTemplate transaction = new TransactionTemplate(transactionManager);
        transaction.executeWithoutResult(status -> {
            stateService.recordPandaFailure(new IllegalStateException("provider unavailable"));
            status.setRollbackOnly();
        });

        assertThat(repository.findByProvider(LecSynchronizationService.PANDASCORE))
                .get()
                .extracting(ProviderSyncState::getStatus, ProviderSyncState::getLastError)
                .containsExactly("FAILED", "provider unavailable");
    }
}
