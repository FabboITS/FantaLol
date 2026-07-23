package com.fantalol.backend.integration.oracle;

import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.InputStream;

final class InMemoryMultipartFile implements MultipartFile {
    private final String name;
    private final byte[] content;

    InMemoryMultipartFile(String name, byte[] content) {
        this.name = name;
        this.content = content;
    }

    @Override public String getName() { return "file"; }
    @Override public String getOriginalFilename() { return name; }
    @Override public String getContentType() { return "text/csv"; }
    @Override public boolean isEmpty() { return content.length == 0; }
    @Override public long getSize() { return content.length; }
    @Override public byte[] getBytes() { return content; }
    @Override public InputStream getInputStream() { return new ByteArrayInputStream(content); }
    @Override public void transferTo(java.io.File dest) throws java.io.IOException {
        java.nio.file.Files.write(dest.toPath(), content);
    }
}
