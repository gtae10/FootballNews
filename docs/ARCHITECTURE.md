# 아키텍처 개요

## 파이프라인

```
뉴스 소스 (RSS + 크롤링)
        │
        ▼
  수집 스케줄러 (Python)
        │
        ▼
   원문 저장소 (DB)
        │
        ▼
 LLM 번역 파이프라인
        │
        ▼
   API 서버 (Spring Boot)
        │
        ▼
 웹 · 모바일 클라이언트
```

## 컴포넌트별 역할

### 1. 뉴스 소스
- 리버풀 팬 매체(고정 태그)와 해외축구 전반을 다루는 대형/전문 매체(구단 자동 감지)를
  함께 수집한다. 공식 RSS가 있는 매체는 RSS로, 없는 매체는 크롤링으로 보완
- 소스 목록은 `collector/sources.py`에서 관리하며, 등록 전 robots.txt/이용약관을 확인해
  AI 요약·재사용을 명시적으로 금지하거나 Claude/Anthropic 크롤러를 차단하는 매체는
  제외한다 (선정 기준은 `sources.py` 주석 및 `docs/LEGAL_NOTES.md` 참고)

### 2. 수집 스케줄러 (`collector/`)
- 주기적으로 신규 기사를 확인하고 원문을 저장소에 적재
- URL 기준 중복 제거
- 백엔드 `GET /clubs`(5대 리그 50개 구단) 기준으로 기사 본문에서 언급된 구단(들)을 자동
  감지해 태깅한다 (`collector/club_matcher.py`). 이적 기사처럼 여러 구단이 함께 언급되면
  다중 태깅되고, 특정 구단이 감지되지 않은 기사(리그 전반 이슈 등)는 태그 없이 저장된다
- 본문에 유명 기자/계정(`collector/trusted_reporters.py`)이 인용된 것으로 감지되면
  (`collector/reporter_detector.py`), 해당 기사의 소스 신뢰도 등급(`source_tier`)을 더
  신뢰도 높은 값으로 갱신한다
- 제목에서 선수명 후보를 규칙 기반으로 추출하고(`collector/player_extractor.py`), 본문에
  이적 관련 키워드가 있으면(`collector/rumor_clusterer.py`) 같은 (선수, 구단) 건을
  루머 스레드로 묶는다. 스레드/교차검증 로직 상세는 [DB_SCHEMA.md](DB_SCHEMA.md#rumor_threads)와
  [API.md](API.md#루머-스레드-타임라인) 참고

### 3. 원문 저장소
- 관계형 DB(PostgreSQL 또는 MySQL) 사용
- 상세 스키마는 [DB_SCHEMA.md](DB_SCHEMA.md) 참고

### 4. 번역 파이프라인 (`translator/`)
- 신규/미번역 기사를 감지해 번역한다. 기본 엔진은 **Argos Translate**(오픈소스,
  오프라인, 무료) — 파파고/구글/DeepL 등 상용 API는 전부 카드 등록이 필요해
  카드 등록 없이 바로 쓸 수 있는 대안으로 도입했다(`translator/argos_engine.py`).
  Claude(Anthropic API) 기반 엔진(`translator/anthropic_engine.py`)과
  GPT(OpenAI API) 기반 엔진(`translator/openai_engine.py`)도 그대로 보존돼
  있어, 번역 품질이 더 중요해지면 `translate.py`의 `ENGINE` 상수(또는
  `TRANSLATOR_ENGINE` 환경 변수)만 바꿔 다시 켤 수 있다.
- 번역 직전에 RSS 원문의 HTML 태그/엔티티와 워드프레스 특유의 피드 푸터를
  제거한다(`html_cleanup.py`) — 그대로 두면 NMT가 링크 URL까지 훼손하는 문제가
  있었다.
- 축구 용어 일관성을 위한 용어집(glossary)을 적용한다. Claude/GPT처럼
  프롬프트를 지원하는 엔진에는 프롬프트에 포함시키고, Argos Translate처럼
  프롬프트 개념이 없는 엔진에는 번역 후 결과 텍스트에 후처리로 치환한다.
- 이미 번역된 기사는 `status`로 구분해 재호출하지 않는다. 상용 API 엔진
  (Claude/GPT)은 개별 기사 번역이 실패해도(인증 에러, rate limit, 빈 응답
  등) 배치 전체를 중단하지 않고 해당 기사만 건너뛴다 — status가 COLLECTED로
  남아 다음 배치 실행 때 자동 재시도된다.
- Argos Translate는 문장 단위 직역에 가까워 Claude/GPT 기반 요약 번역보다
  품질이 낮을 수 있다는 트레이드오프가 있다(상세: `translator/README.md`).
- **우선순위 큐 + 하루 처리 한도**: `status='COLLECTED'`인 기사는 사실상 번역
  대기열이다. `DAILY_TRANSLATION_LIMIT`(기본 300, 환경 변수로 조정)으로 하루
  처리량을 제한해 유료 엔진(OpenAI/Claude) API 비용이 무한정 늘지 않게 한다.
  한도를 넘긴 기사는 버려지지 않고 COLLECTED 상태 그대로 다음 배치(대개
  다음날)로 자동 이월된다. 어떤 기사를 먼저 처리할지는 `translator/priority.py`가
  정한다 — ① `source_tier=1`(대형/공식 매체)이거나 신뢰도 높은 기자가 인용된
  기사(`quoted_reporter`), ② 이적 루머 스레드에 속하고 교차 보도 매체 수
  (`rumor_threads.independent_source_count`)가 많은 기사, ③ 나머지는 발행일
  최신순. 오늘 이미 처리한 건수는 `translations.translated_at`으로 매 실행마다
  다시 세어 확인한다(scheduler.py가 30분마다 새 프로세스로 실행하므로 메모리에
  상태를 들고 있을 수 없음). 이월 건수가 `CARRYOVER_WARNING_THRESHOLD`(기본
  500)를 넘으면 한도 상향을 제안하는 경고 로그를 남긴다.
  - **알려진 상호작용**: `source_tier=1`은 우선순위 1순위이므로, 본문이 영구히
    비어 있어 매번 실패하는 tier-1 기사(예: 만료된 라이브 블로그, 위 "기사
    이미지 썸네일"/본문 크롤링 섹션 참고)도 매 배치마다 큐 맨 앞에서 재시도된다.
    API 비용은 들지 않지만(본문 없음 가드가 호출 전에 막음) 한도 슬롯을 일부
    차지하므로, 이런 기사가 많아지면 로그가 "번역 실패" 줄로 다소 시끄러워질 수
    있다(실제로 확인함, 2026-09-12 세션).

### 5. API 서버 (`backend/`)
- Spring Boot 기반 REST API
- 기사 목록/상세/검색 제공
- 상세 스펙은 [API.md](API.md) 참고

### 6. 클라이언트
- 웹: React (`frontend-web/`)
- 모바일: 추후 React Native로 확장 예정

## 기술 스택 요약

| 영역 | 기술 |
|---|---|
| 수집기 | Python (requests, BeautifulSoup, feedparser) |
| 번역 | Argos Translate (기본, 오프라인/무료) — Claude API 또는 OpenAI API로 교체 가능 |
| 백엔드 | Spring Boot, JPA |
| DB | PostgreSQL / MySQL |
| 웹 프론트엔드 | React |
| 모바일 | React Native (추후) |
