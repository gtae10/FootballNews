package com.liverpool.news.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 로그인이 없어 사용자를 구분할 수 없으므로, 클라이언트 IP 기준 고정 윈도(fixed
 * window) 카운터로 남용을 막는다. 인증/세션 개념이 없는 이 프로젝트 규모에서는
 * bucket4j 같은 라이브러리를 새로 들여오는 것보다 이 편이 간단하다.
 *
 * ponytail: 프로세스 재시작 시 카운터가 초기화되고, 서버를 여러 대로 늘리면
 * 인스턴스별로 따로 세진다(공유 저장소 없음) — 지금처럼 단일 인스턴스에서만
 * 유효하다. 여러 인스턴스로 늘어나면 Redis 등 공유 저장소 기반으로 옮겨야 한다.
 */
@Component
public class ChatRateLimiter {

    private final int maxRequestsPerWindow;
    private final Duration window;
    private final ConcurrentHashMap<String, Bucket> buckets = new ConcurrentHashMap<>();

    public ChatRateLimiter(
            @Value("${app.chat.rate-limit.max-requests:20}") int maxRequestsPerWindow,
            @Value("${app.chat.rate-limit.window-minutes:10}") long windowMinutes
    ) {
        this.maxRequestsPerWindow = maxRequestsPerWindow;
        this.window = Duration.ofMinutes(windowMinutes);
    }

    /** 허용되면 true, 한도를 넘겼으면 false. */
    public boolean tryAcquire(String clientKey) {
        Bucket bucket = buckets.computeIfAbsent(clientKey, key -> new Bucket());
        synchronized (bucket) {
            Instant now = Instant.now();
            if (Duration.between(bucket.windowStart, now).compareTo(window) >= 0) {
                bucket.windowStart = now;
                bucket.count = 0;
            }
            if (bucket.count >= maxRequestsPerWindow) {
                return false;
            }
            bucket.count++;
            return true;
        }
    }

    private static final class Bucket {
        Instant windowStart = Instant.now();
        int count = 0;
    }
}
