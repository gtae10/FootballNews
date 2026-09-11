# DB 스키마 (초안)

## articles

원문 기사 정보

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | BIGINT (PK) | 기사 ID |
| source | VARCHAR | 출처 매체명 |
| original_url | VARCHAR (UNIQUE) | 원문 URL |
| title_original | TEXT | 원문 제목 |
| content_original | TEXT | 원문 본문 |
| published_at | TIMESTAMP | 원문 발행일 |
| collected_at | TIMESTAMP | 수집 시각 |
| status | VARCHAR | COLLECTED / TRANSLATED / PUBLISHED |
| source_tier | INT (nullable) | 소스 신뢰도 등급 (1이 가장 신뢰도 높음, "오늘의 주요 소식" 정렬에 사용). `article_clubs`에 태깅된 구단이 없거나 매체 자체 등급이 있어도, 신뢰도 높은 기자/계정이 인용된 것으로 감지되면(quoted_reporter) 더 낮은(신뢰도 높은) 값으로 갱신될 수 있다 (collector/reporter_detector.py 참고) |
| quoted_reporter | VARCHAR (nullable) | 본문에 인용된 것으로 감지된 유명 기자/계정 이름 (collector/trusted_reporters.py에 등록된 이름 중 하나). 감지되지 않으면 NULL |
| image_url | VARCHAR (nullable) | 대표 이미지 URL. 이미지 파일 자체는 다운로드/재호스팅하지 않고 원본 서버의 URL만 저장하며, 프론트엔드가 이 URL로 직접 이미지를 불러온다(저작권 문제 회피). RSS의 `media:thumbnail`/`media:content`/`enclosure`/본문 내 `<img>` 태그 순으로 시도해 찾고(`collector/rss_collector.py`의 `_extract_image_url`), 못 찾으면 NULL — 이 경우 프론트는 이미지 영역 없이 텍스트만 표시한다. **재수집 없이는 기존 데이터에 소급 적용할 수 없다** (RSS 원본을 다시 조회해야만 얻을 수 있는 값이라, 이 컬럼 도입 이전에 수집된 기사는 전부 NULL로 남는다) |
| category | VARCHAR (nullable) | 기사 카테고리: `MATCH`(경기) / `TRANSFER`(이적) / `PLAYER`(선수 개인 소식) / `OTHER`(리그 전반 이슈 등). `collector/article_classifier.py`가 저장 시점에 규칙 기반으로 채운다 — 이미 `rumor_threads`에 묶인 기사는 최우선으로 `TRANSFER`, 그다음 경기/선수 키워드(`collector/category_keywords.py`), 마지막으로 미클러스터링 이적 키워드(`rumor_clusterer.py`의 스토리 단계 키워드 재사용) 순으로 판정하고 어디에도 안 걸리면 `OTHER`. 이 컬럼 도입 이전에 수집됐거나 아직 소급 배치(`collector/backfill_categories.py`)가 돌지 않은 기사는 NULL일 수 있다 |

기사가 어떤 구단을 다루는지는 `club` 단일 컬럼이 아니라 아래 `article_clubs` 조인 테이블에 다중 값으로 저장한다
(이적 기사처럼 한 기사가 여러 구단을 언급하는 경우가 흔하기 때문). 어떤 구단도 감지되지 않은 기사(리그 전반 이슈 등)는
`article_clubs`에 row 없이 저장될 수 있다.

## article_clubs

기사 ↔ 구단 다대다 태깅 (기사 본문에서 자동 감지된 구단, collector/club_matcher.py 참고)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| article_id | BIGINT (FK -> articles.id) | 태깅된 기사 |
| club_name | VARCHAR | 구단명 (`GET /clubs`가 반환하는 `clubs.name`과 동일한 표기) |

`(article_id, club_name)` 복합 기본키로 관리한다 (같은 기사에 같은 구단이 중복 태깅되지 않는다).

## article_images

기사 원문 페이지 본문을 크롤링해 추가로 찾은 이미지 URL 목록(`collector/body_image_extractor.py`
참고). 대표 이미지(`articles.image_url`)와 동일한 원칙으로 이미지 파일 자체는 다운로드/재호스팅하지
않고 원본 서버 URL만 저장한다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| article_id | BIGINT (FK -> articles.id) | 연결된 기사 |
| position | INT | 원문에 실린 순서(0부터 시작). 백엔드 `Article.images`가 `@OrderColumn`으로 이 컬럼을 관리한다 |
| image_url | VARCHAR (nullable) | 이미지 URL |

`(article_id, position)` 복합 기본키로 관리한다.

기사를 저장(`collector/db.py`의 `save_articles`)할 때마다 원문 페이지를 한 번 더 요청해 본문
컨테이너(`<article>`, `.entry-content` 등 널리 쓰이는 셀렉터를 우선순위대로 시도) 안의 `<img>`
태그를 찾고, 광고/공유버튼/아바타/로고처럼 본문과 무관한 이미지는 클래스명·URL 패턴으로 제외한다
(완벽하지 않을 수 있는 휴리스틱이다). 이미 대표 이미지로 저장된 URL은 중복 노출을 피하려고
결과에서 제외하며, 최대 5개까지만 저장한다. **크롤링이 실패하거나(네트워크 오류, 타임아웃, 4xx/5xx,
소스가 크롤링을 사실상 막는 경우 등) 본문에서 이미지를 하나도 못 찾으면 이 테이블에 아무 row도
남기지 않는다** — 이 경우 프론트는 대표 이미지(`image_url`) 하나만 표시하는 것으로 폴백한다.
`articles` 저장마다 원문 서버에 추가 요청을 보내므로, 요청 사이 최소 지연(`db.py`의
`BODY_IMAGE_REQUEST_DELAY_SECONDS`)을 둔다. **이 기능 도입 이전에 수집된 기사에는 소급 반영되지
않는다** — `collector/backfill_article_images.py`로 별도 소급 배치를 실행해야 한다(사용법은
`collector/README.md` 참고).

## rumor_threads

같은 이적 건(선수 + 구단)으로 묶인 기사들의 스레드. `collector/rumor_clusterer.py`가
채우고 갱신하며, 백엔드는 읽기 전용으로 `GET /rumor-threads`에 노출한다
(`docs/API.md` 참고). 선수명은 정규식 기반 후보 추출(`collector/player_extractor.py`)
결과이므로 완벽하지 않을 수 있다 — 오탐/누락 트레이드오프는 해당 파일 상단 주석 참고.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | BIGINT (PK) | 스레드 ID |
| player_name | VARCHAR | 대표 선수명 후보 (제목에서 추출된 원문 그대로, 정규화되지 않음) |
| club_name | VARCHAR | 연결된 구단명 (`clubs.name`과 동일 표기). 같은 선수라도 구단이 다르면 별도 이적 건으로 보아 스레드도 분리된다 (예: "Isak → Liverpool"과 "Isak → Arsenal"은 다른 스레드) |
| latest_stage | VARCHAR | 스레드에 포함된 기사들 중 가장 진전된 스토리 단계. `UNKNOWN` / `INTEREST` / `NEGOTIATION` / `CONFIRMED` / `OFFICIAL` (이 순서가 진전도 순서) |
| independent_source_count | INT | 스레드 최초 기사 발행 시각으로부터 48시간 이내에 보도한, 서로 다른 `source`(매체)의 수. **"여러 매체가 독립적으로 같은 이야기를 보도했다"는 뜻일 뿐 "이적이 사실로 확인됐다"는 뜻이 아니다** — 의도적으로 `verified_*`가 아닌 이 이름을 썼다 |
| cross_reported | BOOLEAN | `independent_source_count >= 2`일 때 `true`. 같은 매체가 같은 얘기를 여러 번 써도 소스 1개로만 카운트된다 |
| created_at | DATETIME | 스레드 생성 시각 |
| updated_at | DATETIME | 마지막으로 기사가 합류하거나 단계가 갱신된 시각 |

## rumor_thread_articles

루머 스레드 ↔ 기사 다대다 연결 (기사 하나가 여러 선수/구단을 함께 언급하면 여러
스레드에 동시에 연결될 수 있다).

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | BIGINT (PK) | 연결 ID |
| rumor_thread_id | BIGINT (FK -> rumor_threads.id) | 스레드 |
| article_id | BIGINT (FK -> articles.id) | 연결된 기사 |
| story_stage | VARCHAR | 이 기사 자체의 스토리 단계 (제목+본문 키워드로 감지, `collector/rumor_clusterer.py`의 `detect_story_stage` 참고). `UNKNOWN`이면 애초에 클러스터링 대상에서 제외되므로(경기 리포트 등 이적과 무관한 기사가 스레드에 섞이는 것을 막기 위함) 이 컬럼에는 `UNKNOWN`이 저장되지 않는다 |

클러스터링 규칙: 새 기사가 (구단 태그 있음 + 이적 키워드로 스토리 단계 판정됨 +
선수명 후보 추출됨) 조건을 모두 만족하면, 같은 (선수명, 구단) 조합의 기존 스레드 중
최근 14일 이내 기사가 있는 스레드에 합류시키고, 없으면 새 스레드를 만든다. 세 조건
중 하나라도 없으면(구단 미태깅, UNKNOWN 단계, 선수명 후보 없음) 클러스터링하지 않는다.

## translations

번역 결과 (기사와 1:1)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | BIGINT (PK) | 번역 ID |
| article_id | BIGINT (FK -> articles.id) | 연결된 기사 |
| title_ko | TEXT | 번역된 제목 |
| content_ko | TEXT | 번역/요약된 본문 |
| model_version | VARCHAR | 사용한 LLM 모델 버전 |
| translated_at | TIMESTAMP | 번역 시각 |

## users

Google OAuth 로그인 사용자

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | BIGINT (PK) | 사용자 ID |
| email | VARCHAR (UNIQUE) | 구글 계정 이메일 |
| nickname | VARCHAR (nullable) | 닉네임, 미설정 시 이메일로 표시 |
| created_at | TIMESTAMP | 가입 시각 |

## clubs

온보딩/설정에서 선택 가능한 구단 목록 (5대 리그 주요 구단 시드 데이터)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | BIGINT (PK) | 구단 ID |
| name | VARCHAR | 구단명 |
| league | VARCHAR | EPL / LA_LIGA / BUNDESLIGA / SERIE_A / LIGUE_1 |

## user_preferences

사용자별 온보딩 설정 (1:1 users)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | BIGINT (PK) | ID |
| user_id | BIGINT (FK -> users.id, UNIQUE) | 사용자 |
| notification_trust_level | INT | 알림 신뢰도 1(공식 소스만) ~ 5(모든 소스) |
| favorite_club_id | BIGINT (FK -> clubs.id, nullable) | 관심 구단(clubs) 중 대표로 지정한 "최애팀". 관심 구단과 달리 다대일 단방향 관계이며, 아직 최애팀을 지정하지 않은 사용자는 NULL이다 |

`user_preference_clubs` 조인 테이블로 `user_preferences` ↔ `clubs` 다대다 관계를 관리한다
(사용자의 온보딩 완료 여부는 이 테이블에 row가 있는지로 판단한다).

최애팀으로 지정한 구단이 관심 구단(`user_preference_clubs`) 목록에 없으면 에러를 반환하는
대신 관심 구단 목록에 자동으로 추가한다 (`UserPreferenceService.savePreference` 참고) —
한 번의 `PUT`으로 "관심 구단 추가 + 최애팀 지정"이 동시에 되는 편이 별도 400을 반환하는
것보다 자연스럽다고 판단했다. 온보딩/설정 UI 자체는 이미 선택된 관심 구단 중에서만 최애팀을
고르게 하므로, 이 자동 추가 경로는 API를 직접 호출하는 경우에 대한 방어 장치다.

## reporter_suggestions

사용자가 제보한, 아직 수집되지 않은 기자 정보

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | BIGINT (PK) | 제보 ID |
| user_id | BIGINT (FK -> users.id) | 제보한 사용자 |
| twitter_handle | VARCHAR | 기자의 트위터(X) 핸들 (필수) |
| name | VARCHAR (nullable) | 기자 이름 (선택) |
| league | VARCHAR (nullable) | 주로 다루는 리그, `clubs.league`와 동일한 값 (선택) |
| memo | TEXT (nullable) | 추가 메모 (선택) |
| created_at | TIMESTAMP | 제보 시각 |

계정 탈퇴 시 해당 사용자의 제보는 함께 삭제된다.

## 인덱스 제안

- `articles.original_url` UNIQUE 인덱스 (중복 수집 방지)
- `articles.published_at` 인덱스 (최신순 정렬/필터)
- `article_clubs.club_name` 인덱스 (구단별 필터 조회)
- `translations.article_id` 인덱스 (조인 성능)
- `users.email` UNIQUE 인덱스 (구글 계정당 1 row)
- `reporter_suggestions.user_id` 인덱스 (내 제보 목록 조회)

## 마이그레이션 메모 (club 단일 컬럼 → article_clubs)

기존에는 `articles.club` VARCHAR 단일 컬럼에 리버풀 한 구단만 저장했다. 다중 구단 태깅 도입 후:

1. 백엔드 재기동 시 `ddl-auto: update`가 `article_clubs` 테이블과 `articles.quoted_reporter` 컬럼을 자동 생성한다
   (기존 `articles.club` 컬럼은 자동으로 삭제되지 않는다).
2. 기존 데이터(리버풀 150건 등)를 새 구조로 옮기려면 아래 SQL을 한 번 실행한다.
   ```sql
   INSERT INTO article_clubs (article_id, club_name)
   SELECT id, club FROM articles WHERE club IS NOT NULL AND club <> '';
   ```
3. 위 마이그레이션과 애플리케이션 배포(신규 컬렉터/백엔드 코드) 확인이 끝나면 안 쓰는 컬럼을 정리한다.
   ```sql
   ALTER TABLE articles DROP COLUMN club;
   ```

**실제로는 위 SQL 대신 `collector/retag_articles.py`를 실행해 마이그레이션했다** (2026-09). 그 시점에
이미 `articles.club` 컬럼 자체가 존재하지 않는 상태였고(레거시 단일 컬럼 스키마가 실제 DB에 반영된
적이 없었음), club_matcher.py의 본문 기반 구단 감지 + sources.py의 forced_club 규칙을 그대로 재사용해
기존 150건을 재태깅하는 편이 더 정확했다. 같은 이유로 `articles.quoted_reporter`(기자 인용 감지) 도입
후에도 기존 데이터에는 소급 반영되지 않았는데, 이는 `collector/retag_reporters.py`로 채웠다. 두
스크립트 모두 이미 태그/감지된 기사는 건드리지 않아 여러 번 실행해도 안전하다 — 사용법은
`collector/README.md`의 "소급 재태깅" 절 참고.
