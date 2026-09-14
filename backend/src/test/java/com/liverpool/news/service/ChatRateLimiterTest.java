package com.liverpool.news.service;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class ChatRateLimiterTest {

    @Test
    void 한도_안에서는_계속_허용한다() {
        ChatRateLimiter limiter = new ChatRateLimiter(3, 10);

        assertThat(limiter.tryAcquire("1.2.3.4")).isTrue();
        assertThat(limiter.tryAcquire("1.2.3.4")).isTrue();
        assertThat(limiter.tryAcquire("1.2.3.4")).isTrue();
    }

    @Test
    void 한도를_넘으면_거부한다() {
        ChatRateLimiter limiter = new ChatRateLimiter(2, 10);

        assertThat(limiter.tryAcquire("1.2.3.4")).isTrue();
        assertThat(limiter.tryAcquire("1.2.3.4")).isTrue();
        assertThat(limiter.tryAcquire("1.2.3.4")).isFalse();
    }

    @Test
    void 클라이언트별로_따로_카운트한다() {
        ChatRateLimiter limiter = new ChatRateLimiter(1, 10);

        assertThat(limiter.tryAcquire("1.1.1.1")).isTrue();
        assertThat(limiter.tryAcquire("2.2.2.2")).isTrue();
        assertThat(limiter.tryAcquire("1.1.1.1")).isFalse();
        assertThat(limiter.tryAcquire("2.2.2.2")).isFalse();
    }
}
