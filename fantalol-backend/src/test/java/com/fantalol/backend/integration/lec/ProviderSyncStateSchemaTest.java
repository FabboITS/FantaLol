package com.fantalol.backend.integration.lec;

import jakarta.persistence.Column;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Field;

import static org.assertj.core.api.Assertions.assertThat;

class ProviderSyncStateSchemaTest {
    @Test
    void storesPandaSnapshotsInLongTextColumn() throws Exception {
        Field field = ProviderSyncState.class.getDeclaredField("providerSnapshot");
        assertThat(field.getAnnotation(Column.class).columnDefinition()).isEqualToIgnoringCase("LONGTEXT");
    }
}
