package com.fantalol.backend.integration.lec;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(LecSyncProperties.class)
public class LecIntegrationConfiguration {
}
