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

### 4. LLM 번역 파이프라인 (`translator/`)
- 신규/미번역 기사를 감지해 LLM API로 번역
- 축구 용어 일관성을 위한 용어집(glossary) 적용
- 이미 번역된 기사는 캐싱하여 재호출 방지

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
| 번역 | LLM API (Claude/GPT) |
| 백엔드 | Spring Boot, JPA |
| DB | PostgreSQL / MySQL |
| 웹 프론트엔드 | React |
| 모바일 | React Native (추후) |
