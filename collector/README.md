# Collector

해외축구 전반(5대 리그 50개 구단) 뉴스를 RSS와 크롤링으로 수집하는 Python 모듈입니다.
리버풀 팬 매체는 계속 리버풀 전용으로 유지하고, 그 외 소스는 기사 본문에서 언급된 구단을
자동 감지해 태깅합니다. 신뢰도 높은 기자/계정(Fabrizio Romano 등)이 인용된 것으로 감지되면
해당 기사의 `source_tier`를 더 신뢰도 높은 값으로 갱신합니다.

## 실행 방법

```bash
pip install -r requirements.txt --break-system-packages
cp .env.example .env  # 필요 시 COLLECTOR_DB_URL 조정
```

### 일반 실행 (평소 주기 수집 + 번역 — 최신 기사만)

```bash
python scheduler.py
```

30분 간격으로 각 RSS 소스의 최신 페이지(소스당 15~20건)만 조회한다. 아카이브는
훑지 않으므로 매 실행이 빠르고 요청 수도 적다. 수집이 끝나면 바로 이어서
`../translator/translate.py`를 별도 파이썬 프로세스로 실행해 새로 수집된 기사를
번역한다(`run_collection_and_translation_job`, 2026-09-11 추가) — collector와
translator는 별도 모듈이라(각자 `db.py`를 따로 관리, 둘 다 이름이 같아 같은
프로세스로 import하면 충돌함) 같은 프로세스에 합치지 않고 서브프로세스로 분리했다.
번역 엔진은 `TRANSLATOR_ENGINE` 환경 변수를 따르며, 지정하지 않으면 `openai`가
기본값이다(이 환경엔 Argos 오프라인 모델이 설치돼 있지 않아 `translate.py` 자체
기본값인 `argos`로는 실제 번역이 안 됨 — `docs/FEATURE_STATUS.md` 11번 참고). 번역
배치가 실패해도(네트워크 오류, `OPENAI_API_KEY` 누락 등) 수집 스케줄러 자체는
멈추지 않고 다음 30분 주기에 재시도된다.

### 백필 실행 (과거 기사 수집 — 필요할 때만 수동 실행)

```bash
python backfill.py                # 소스당 최대 5페이지까지 과거 아카이브 순회 (기본값)
python backfill.py --pages 10     # 페이지 수를 직접 지정
```

`scheduler.py`와 완전히 분리된 1회성 스크립트다. 세 RSS 소스 모두 `?paged=N` 쿼리
파라미터로 과거 페이지 조회를 지원함을 확인했고(2026-09 기준, 최소 30페이지까지 정상
응답), `backfill.py`는 이를 이용해 페이지를 순회하며 수집한다. 신규 소스를 추가한
직후처럼 과거 데이터를 한 번에 많이 확보해야 할 때만 수동으로 실행한다 — 평소
스케줄러 실행에는 전혀 영향을 주지 않는다. 소스/페이지 요청 사이에 최소 1.5초
지연을 둔다(`backfill.REQUEST_DELAY_SECONDS`).

`COLLECTOR_DB_URL`을 지정하지 않으면 `backend/docker-compose.yml`로 띄운 로컬 MySQL
(`mysql+pymysql://root:password@localhost:3306/liverpool_news`)에 연결을 시도한다.
backend와 동일한 `articles`/`article_clubs` 테이블 스키마를 사용하므로, 먼저 backend를
한 번 실행해 테이블이 생성된 상태여야 한다 (`spring.jpa.hibernate.ddl-auto=update`).
기존에 `articles.club` 단일 컬럼으로 저장된 데이터가 있다면 `docs/DB_SCHEMA.md`의
마이그레이션 SQL을 먼저 실행해야 한다.

구단 자동 태깅은 `COLLECTOR_BACKEND_API_URL`(기본 `http://localhost:8080/api/v1`)로
백엔드 `GET /clubs`를 호출해 구단 목록을 가져온다. 백엔드가 떠 있지 않으면 이 호출은
실패하지만 수집 자체를 막지는 않는다 — 이 경우 본문 기반 구단 감지는 건너뛰고
(리버풀 팬 매체처럼) 소스에 고정된 `forced_club`만 적용된다.

`collector/.env`가 있으면 `db.py` import 시점에 `python-dotenv`가 자동으로 읽어들여
별도 `export` 없이 실행해도 값이 적용된다. `.env`가 없으면 에러 없이 위 기본 접속
정보로 동작한다.

### 소급 재태깅 (기존에 저장된 기사에 새 로직 반영)

`save_articles()`(db.py)의 구단 자동 태깅과 기자 인용 감지는 **신규로 저장되는
기사에만** 적용된다. 이 로직들이 도입되기 전에 이미 저장돼 있던 기사나, 신규 소스
추가/로직 변경 전에 수집된 기사는 소급 반영되지 않는다. 아래 두 스크립트는 그
공백을 메우는 1회성 배치로, 이미 태깅/감지된 기사는 건드리지 않으므로 몇 번을
다시 실행해도 안전하다(idempotent).

```bash
python retag_articles.py   # article_clubs에 태그가 없는 기사를 club_matcher로 재태깅
python retag_reporters.py  # quoted_reporter가 비어 있는 기사에 기자 인용 감지 재적용
```

신규 소스를 추가하거나 `trusted_reporters.py`에 기자를 추가한 직후처럼, 기존
데이터에도 새 규칙을 반영하고 싶을 때 실행한다.

### 루머 스레드 소급 클러스터링

```bash
python build_rumor_threads.py  # rumor_thread_articles에 연결이 없는 기사를 발행일순으로 클러스터링
```

`save_articles()`(db.py)는 신규로 저장되는 기사에만 루머 스레드 클러스터링을
적용한다(`rumor_clusterer.py`). 이 스크립트 도입 전 저장된 기사에 소급 적용할 때
실행한다. 이미 스레드에 연결된 기사는 건드리지 않으므로 여러 번 실행해도
안전하다(idempotent). 실행 전 backend를 한 번 띄워 `rumor_threads`/
`rumor_thread_articles` 테이블이 생성된 상태여야 하고(`ddl-auto=update`),
`GET /clubs` 호출이 가능해야 한다(구단 별칭을 선수명 후보 제외 목록에 포함하기 위해).

### 카테고리 소급 분류

```bash
python backfill_categories.py  # category가 NULL인 기사를 모두 MATCH/TRANSFER/PLAYER/OTHER로 분류
```

`save_articles()`(db.py)는 신규로 저장되는 기사에만 카테고리 분류를
적용한다(`article_classifier.py`). 이 스크립트 도입 전 저장된 기사에 소급 적용할
때 실행한다. `build_rumor_threads.py`를 먼저 실행해 루머 스레드 클러스터링을
최대한 소급 적용해둔 뒤 이 스크립트를 실행하는 편이 좋다 — TRANSFER 판정의
최우선 조건이 "이미 rumor_thread_articles에 연결돼 있는가"이기 때문이다. 이미
category가 채워진 기사는 건드리지 않으므로 여러 번 실행해도 안전하다(idempotent).

### 본문 이미지 소급 크롤링

```bash
python backfill_article_images.py           # article_images에 row가 없는 기사를 모두 크롤링
python backfill_article_images.py --limit 50 # 앞 50건만 처리 (테스트용)
```

`save_articles()`(db.py)는 신규로 저장되는 기사에만 본문 이미지 크롤링을
적용한다(`body_image_extractor.py`). 이 기능 도입 전 저장된 기사는 `article_images`에
아무 row도 없으므로, 이 스크립트로 소급 크롤링한다. 기사 하나를 처리할 때마다 원문
서버에 요청을 보내므로 `db.BODY_IMAGE_REQUEST_DELAY_SECONDS`(1초)만큼 지연하고,
기사 하나가 끝날 때마다 즉시 커밋한다 — 중간에 중단해도 이미 처리한 결과는 남고
재실행하면 이어서 처리된다. 다만 "크롤링했지만 이미지를 못 찾음"과 "아직 시도
안 함"을 구분하지 못해(둘 다 row 0개) 재실행 시 못 찾았던 기사도 다시 시도하므로,
소스에 반복 요청을 보내게 된다는 점을 감안해 필요할 때만 실행한다.

## 파일 구성

- `sources.py`: 수집 대상 소스 목록 (RSS URL, 크롤링 대상 사이트). 등록된 소스와
  선정 기준(robots.txt/이용약관 확인 결과 포함)은 파일 내 주석 참고.
- `rss_collector.py`: RSS 기반 수집 로직. `max_pages`/`delay_seconds`로 과거 페이지
  순회를 지원한다 (기본값은 1페이지만 조회 — 평소 실행과 동일하게 동작). 대표 이미지
  URL도 함께 추출한다(`_extract_image_url`) — `media:thumbnail`/`media:content`/
  `enclosure`/본문 내 `<img>` 태그 순으로 시도하고, 이미지 파일 자체는 다운로드/재호스팅
  하지 않고 URL만 저장한다(저작권 문제 회피). 이 컬럼 도입 이전에 수집된 기사는 RSS
  원본을 다시 조회해야만 채울 수 있어 소급 적용되지 않는다.
- `club_matcher.py`: 백엔드 `GET /clubs` 기준으로 기사 본문에서 언급된 구단(들)을
  자동 감지하는 로직 (별칭 매핑 포함).
- `trusted_reporters.py`: 인용 감지 대상 유명 기자/계정 목록과 신뢰도 등급(tier).
- `reporter_detector.py`: 기사 본문에서 `trusted_reporters.py`에 등록된 기자/계정의
  인용을 감지하고, 감지되면 `source_tier`를 더 신뢰도 높은 값으로만 갱신하는 로직.
- `crawler.py`: RSS가 없는 사이트를 위한 크롤링 로직 (현재 등록된 소스는 모두 RSS
  페이지네이션으로 과거 기사까지 수집 가능하므로 실제 사용되지는 않는다)
- `scheduler.py`: 주기적 실행 스케줄러 (30분 간격, 최신 페이지만 조회)
- `backfill.py`: 과거 기사 백필 1회성 스크립트 (소스당 여러 페이지 순회, 요청 간 지연 포함)
- `body_image_extractor.py`: 기사 원문 페이지를 요청해 본문 영역(`<article>` 등) 안의
  이미지 URL을 추가로 추출하는 로직. 광고/공유버튼/아바타/로고 등은 클래스명·URL
  패턴으로 제외하는 휴리스틱이라 완벽하지 않을 수 있다. 크롤링이 실패하면(네트워크
  오류, 소스가 사실상 크롤링을 막는 경우 등) 빈 리스트를 반환해 기존 대표 이미지
  하나만 남기는 폴백으로 자연스럽게 이어진다.
- `db.py`: 수집한 기사를 `articles`/`article_clubs`/`article_images` 테이블에 저장
  (원문 URL 기준 중복 제거, 구단 자동 태깅·기자 인용 감지·본문 이미지 크롤링을
  저장 직전에 적용)
- `retag_articles.py`: article_clubs에 태그가 없는 기존 기사에 club_matcher를 소급
  적용하는 1회성 배치 (신규 저장 시에만 적용되는 구단 태깅의 공백을 메운다)
- `retag_reporters.py`: quoted_reporter가 비어 있는 기존 기사에 기자 인용 감지를
  소급 적용하는 1회성 배치 (신규 저장 시에만 적용되는 인용 감지의 공백을 메운다)
- `player_extractor.py`: 제목에서 대문자로 시작하는 연속 단어를 선수명 후보로 추출하는
  규칙 기반 로직 (구단명/기자명/대회명/스톱워드 제외). 완벽한 개체명 인식이 아니므로
  오탐/누락 트레이드오프가 있다 — 파일 상단 주석 참고
- `rumor_clusterer.py`: (선수명, 구단) 조합으로 기사를 루머 스레드로 묶고, 본문 키워드로
  스토리 단계(INTEREST~OFFICIAL)를 판정하고, 48시간 이내 서로 다른 소스 수로 교차보도
  여부(cross_reported)를 계산하는 로직
- `build_rumor_threads.py`: 기존 기사에 루머 스레드 클러스터링을 소급 적용하는 1회성 배치
- `category_keywords.py`: 기사 카테고리(MATCH/PLAYER) 판정에 쓰는 키워드 목록. TRANSFER
  판정은 별도 목록 없이 rumor_clusterer.py의 이적 스토리 단계 키워드를 재사용한다
  (article_classifier.py 참고) — 키워드를 튜닝하고 싶으면 이 파일을 수정한다.
- `article_classifier.py`: 기사를 MATCH/TRANSFER/PLAYER/OTHER로 분류하는 규칙 기반 로직.
  이미 루머 스레드에 묶인 기사를 최우선으로 TRANSFER 처리하고, 그다음 경기/선수 키워드,
  마지막으로 미클러스터링 이적 키워드 순으로 판정한다 (우선순위는 파일 상단 주석 참고).
- `backfill_categories.py`: 기존 기사에 카테고리 분류를 소급 적용하는 1회성 배치
- `backfill_article_images.py`: 기존 기사에 본문 이미지 크롤링을 소급 적용하는 1회성 배치
- `tests/`: 단위/통합 테스트 (외부 네트워크 호출 없이 mock 또는 in-memory DB 사용)
