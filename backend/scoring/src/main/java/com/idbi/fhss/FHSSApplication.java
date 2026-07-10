package com.idbi.fhss;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication(scanBasePackages = {
    "com.idbi.fhss.scoring",
    "com.idbi.fhss.common"
})
public class FHSSApplication {
    public static void main(String[] args) {
        SpringApplication.run(FHSSApplication.class, args);
    }
}
