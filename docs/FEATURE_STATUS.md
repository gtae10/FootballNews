# 기능 구현 현황

이 문서는 코드/DB/테스트를 실제로 대조해 확인한 "사실"만 기록합니다. 추측이나 계획은 넣지 않습니다.

**확인 시점**: 2026-09-11 (최초 작성 2026-09-07). **확인 방법**: git 커밋 로그, 로컬 MySQL80(`footballnews` DB) 직접 조회, 각 모듈 테스트 스위트 실행(백엔드 `./gradlew test`, collector/translator `pytest`, 프론트 `vitest run`), 일부는 실제로 서버를 띄워 브라우저로 확인.

**새 세션을 시작하기 전에 이 문서를 먼저 읽으세요.**

> **갱신 이력**: 2026-09-07 최초 작성 시점엔 최애팀/카테고리 분류가 미커밋 상태였으나, 같은 날 커밋 `d362233`(카테고리 분류), `93ee6ca`(최애팀), `c89dbde`(이 문서 자체)로 커밋 완료됨. 아래 4/8번 항목은 이 커밋 반영 후 내용임. 2026-09-11 세션에서 번역 배치 재개 완료(11번), 기사 수집량 확대(14번, 신규), 상세 페이지 본문 이미지(15번, 신규)를 추가했고, 그 세션 작업분은 미커밋 상태로 남아있었음. 2026-09-12 세션에서 전체 테스트 재확인(백엔드 54개/collector 155개/프론트 50개, 전부 통과) 후 커밋 완료: `a1b9d05`("433" 리브랜딩), `31e82c5`(12번 스케줄러 자동연결), `92dd94d`(14번 소스 확대), `d26e2b9`(15번 본문 이미지). 아래 12/14/15번 항목의 "미커밋" 표기는 이 커밋 반영 후 내용으로 갱신함.

---

## 기능별 현황

### 1. 로그인 (Google OAuth)

**✅ 완료** (커밋 `c443e2e`, 2026-09-04)

- 코드: `SecurityConfig`, `AuthController`, `JwtService`, `OAuth2LoginFailureHandler` (backend)
- DB: `users` 테이블 실사용 데이터 1건 확인
- 테스트: `AuthControllerTest`, `JwtServiceTest`, `OAuth2LoginFailureHandlerTest`, `UserControllerTest` — 백엔드 전체 53개 테스트에 포함되어 통과 확인(2026-09-07 재실행)

### 2. 게스트 모드

**✅ 완료** (커밋 `42806c7`, 2026-09-05)

- 코드: `AuthContext`의 `isGuest` 상태(프론트엔드 전용, 백엔드 변경 없음 — 커밋 메시지에 명시). 설정/관심 구단 저장/기자 제보 등 로그인 필요 기능은 게스트 상태에서 안내와 함께 막힘
- DB: 해당 없음(프론트 전용 기능)
- 테스트: `LoginPage.test.jsx`, `AuthContext.test.jsx`, `FeedPage.test.jsx`(게스트 시나리오), `SettingsPage.test.jsx`(게스트 시나리오), `FavoriteTeamSection.test.jsx`(게스트 시나리오) — 전부 통과(2026-09-07 재실행)
- 브라우저 확인: 2026-09-06 세션에서 게스트로 피드 진입 및 렌더링 직접 확인함

### 3. 온보딩 (관심 구단, 신뢰도 단계)

**⚠️ 부분 구현** — 기능 자체는 동작하지만 핵심 플로우 자동 테스트가 없음

- 코드: `OnboardingPage.jsx`의 구단 선택(다중 선택) + 신뢰도 단계(1~5) 선택 + 3단계 위저드 — 커밋 `c443e2e`(2026-09-04)부터 존재
- DB: `user_preferences` + `user_preference_clubs` 조인 테이블에 실사용 데이터 1건 확인 (온보딩을 실제로 완료한 사용자가 있다는 뜻)
- 테스트: **빠짐.** `OnboardingPage.test.jsx` 자체가 이번 세션(2026-09-06)에서 처음 생겼는데, 그 안의 테스트 4개는 전부 "최애팀 선택" 시나리오만 다루고 있고(아래 4번 항목), 구단 선택/신뢰도 단계 저장이라는 핵심 플로우를 검증하는 테스트는 커밋 이력 전체에 한 번도 없었음. CLAUDE.md의 "새 기능엔 테스트 필수" 규칙이 최초 구현 시점에 지켜지지 않은 사례
- 마지막 확인: 커밋 `c443e2e` (2026-09-04) — 코드/DB 기준. 테스트 공백은 지금(2026-09-07) 확인한 사실

### 4. 최애팀 (favoriteClub)

**✅ 완료** (커밋 `93ee6ca`, 2026-09-07)

- 코드: `UserPreference.favoriteClub`(Club 다대일 단방향, nullable), `UserPreferenceRequest`/`Response`의 `favoriteClubId`/`favoriteClub`, 온보딩·설정 페이지의 ★ 칩 UI, `FavoriteTeamSection` 컴포넌트(피드 상단, club/category 필터와 무관하게 항상 최애팀 기준 고정)
- 설계 결정: 관심 구단 목록에 없는 구단을 최애팀으로 지정하면 에러 대신 관심 구단에 자동 추가함 (`UserPreferenceService.savePreference` 주석 참고)
- DB: `user_preferences.favorite_club_id` 컬럼 + `clubs.id` FK 제약조건 — 2026-09-06 `./gradlew bootRun` 최초 실행 시 Hibernate가 생성하는 것을 로그로 직접 확인함(그 전까지 이 DB엔 컬럼 자체가 없었음). 실사용 데이터는 아직 0건(최애팀을 설정한 사용자 없음)
- 테스트: 백엔드 `UserPreferenceServiceTest`/`UserPreferenceControllerTest`, 프론트 `FavoriteTeamSection.test.jsx`/`OnboardingPage.test.jsx`/`SettingsPage.test.jsx` — 전부 통과(2026-09-07 재실행: 백엔드 53개, 프론트 39개 중 포함)

### 5. 구단 자동 태깅 (article_clubs)

**✅ 완료** (커밋 `c443e2e`, 2026-09-04)

- 코드: `collector/club_matcher.py` (`detect_clubs`, 별칭 매칭)
- DB: `article_clubs` 조인 테이블 529건 (기사 477건 대비 — 기사 하나가 여러 구단을 언급하는 경우 포함)
- 테스트: `collector/tests/test_club_matcher.py` — collector 전체 124개 테스트에 포함되어 통과(2026-09-07 재실행)

### 6. 기자 인용 감지 (quoted_reporter)

**✅ 완료** (커밋 `c443e2e`, 2026-09-04)

- 코드: `collector/reporter_detector.py`, `collector/trusted_reporters.py`(등록된 신뢰 기자/계정 목록과 대조)
- DB: `articles.quoted_reporter` 채워진 기사 7건 / 477건 확인(실제 감지 발생)
- 테스트: `collector/tests/test_reporter_detector.py` — 통과(2026-09-07 재실행)

### 7. 루머 스레드 클러스터링 + 교차검증 배지

**✅ 완료** (커밋 `cc191e7`, 2026-09-05)

- 코드: `collector/rumor_clusterer.py`(스토리 단계 판정 + 스레드 클러스터링), `collector/build_rumor_threads.py`(소급 배치), 백엔드 `RumorThreadController`/`RumorThreadRepository`
- 참고: `rumor_clusterer.py`는 2026-09-06 카테고리 분류 키워드 보강 작업 때문에 `_STAGE_KEYWORDS`가 추가로 수정됐음(커밋 `d362233`에 포함) — 루머 클러스터링 자체의 신규 기능은 아니고 기존 스테이지 판정 키워드 확장
- DB: `rumor_threads` 18건, `rumor_thread_articles` 21건 연결. **`cross_reported=true`인 스레드는 현재 0건** — 기능 자체는 동작하지만(로직/테스트로 확인됨), 지금 이 DB의 실제 데이터에서는 아직 "48시간 내 2개 이상 매체가 보도"한 사례가 나타나지 않았다는 뜻(결함 아님, 데이터 양이 적어서일 가능성이 높음)
- 테스트: 백엔드 `RumorThreadControllerTest`/`RumorThreadRepositoryTest`, collector `test_rumor_clusterer.py`/`test_build_rumor_threads.py` — 전부 통과(2026-09-07 재실행)

### 8. 카테고리 분류 (MATCH/TRANSFER/PLAYER/OTHER)

**✅ 완료** (커밋 `d362233`, 2026-09-07)

- 코드: `ArticleCategory` enum, `collector/article_classifier.py`(규칙 기반 분류, 우선순위: 루머 스레드 클러스터링 > MATCH 키워드 > PLAYER 키워드 > 미클러스터링 이적 키워드 > OTHER), `collector/category_keywords.py`(MATCH/PLAYER 키워드), `collector/backfill_categories.py`(소급 배치), `collector/db.py`의 `save_articles`가 신규 수집 시점에 자동 분류하도록 연결됨
- DB: `articles.category` 컬럼 — 2026-09-06 최초 `bootRun` 시 Hibernate가 생성(그 전엔 컬럼 없음). 실제 소급 적용 + 키워드 2차 보강 후 최종 분포(2026-09-07 기준, 총 477건): MATCH 36 / TRANSFER 102 / PLAYER 10 / OTHER 329, NULL 0건. (키워드 보강 전 370건 기준 최초 분포는 MATCH 17 / TRANSFER 55 / PLAYER 9 / OTHER 289였음 — 이후 신규 수집 107건이 자동 분류되며 총량과 비율이 변함)
- 알려진 한계(의도적으로 보류): 하이픈 없는 스코어라인("Newcastle 2 Liverpool 2" 형식), "proposed move"/"approach"처럼 오탐 위험이 큰 표현은 키워드에 추가하지 않음. OTHER 비중은 실제로 상당수가 킷 발매/굿즈/심판 판정 논란/팟캐스트 세그먼트 등 "리그 전반 이슈"라 정당한 분류로 판단됨(표본 검토 완료)
- 테스트: 백엔드 `ArticleControllerTest`/`ArticleRepositoryTest`, collector `test_article_classifier.py`/`test_backfill_categories.py`/`test_rumor_clusterer.py`(스테이지 키워드) — 전부 통과(2026-09-07 재실행)

### 9. 기사 이미지 썸네일

**✅ 완료** (커밋 `42806c7`, 2026-09-05)

- 코드: `collector/rss_collector.py`의 `_extract_image_url`(media:thumbnail → media:content → enclosure → 본문 첫 `<img>` 순, 못 찾으면 None), `articles.image_url` 저장, 프론트 `FeedPage.jsx`가 썸네일 렌더링 + `onError`로 실패 시 이미지 영역만 숨김
- 설계: 이미지 파일 자체는 다운로드/재호스팅하지 않고 URL만 저장(저작권 회피). **기존 데이터 소급 적용 불가** — RSS를 다시 가져와야만 얻을 수 있는 값이라 이 컬럼 도입 이전 기사는 영구히 NULL로 남음(재수집 필요, 문서화된 의도적 결정)
- DB: `image_url` 채워진 기사 75건 / 477건. 2026-09-05 이전 수집분(370건)은 전부 NULL — 문서화된 "소급 불가" 판단과 정확히 일치함을 확인
- 실제 라이브 검증(2026-09-06): 7개 RSS 소스 중 5곳(Empire of The Kop, Sky Sports, Independent, Football365, 90min)에서 이미지 추출 확인, 2곳(The Anfield Wrap, Anfield Watch)은 원본 RSS 피드 자체에 이미지 메타데이터가 없어서 0건(파싱 버그 아님, 원인 직접 확인함). 브라우저로 썸네일 렌더링 및 무이미지 폴백(텍스트만 표시) 둘 다 스크린샷으로 확인함
- 테스트: `collector/tests/test_rss_collector.py`(이미지 태그 있음/없음 케이스) — 통과(2026-09-07 재실행)

### 10. 검색 (keyword)

**✅ 완료** (커밋 `c443e2e`, 2026-09-04)

- 코드: `ArticleRepository.search()` — `club`/`category`/`keyword`를 AND 조건으로 동시 적용, 번역 제목(`titleKo`) 또는 원문 제목(`titleOriginal`) 부분 일치(대소문자 무시)로 검색
- DB: 해당 없음(쿼리 로직, 별도 인덱스 테이블 없음)
- 테스트: `ArticleRepositoryTest`/`ArticleControllerTest` — 통과(2026-09-07 재실행)

### 11. 번역

**⚠️ 사실상 비활성화 상태** (엔진 전환 커밋 `90e6233`, `a961c12`, 2026-09-05)

- 코드: `translator/translate.py`의 `ENGINE = "argos"`(기본, 오프라인/무료, `TRANSLATOR_ENGINE` 환경 변수로도 설정 가능). Claude(Anthropic) 기반 `anthropic_engine.py`는 그대로 보존(`ENGINE` 값만 바꾸면 전환 가능, `ANTHROPIC_API_KEY` 필요). 2026-09-07 GPT(OpenAI) 기반 `openai_engine.py`를 세 번째 선택지로 추가(`ENGINE = "openai"`, `OPENAI_API_KEY` 필요, 기본 모델 `gpt-5-mini`). 상용 API 엔진 두 개 모두 개별 기사 번역 실패 시 `TranslationError`/일반 예외를 던지고 `run_translation_batch()`가 잡아 해당 기사만 건너뛰도록(status COLLECTED 유지, 재시도) 처리 추가
- **비활성화 이유**: 사용자 확인(2026-09-06) — Argos Translate 번역 품질 문제로 번역 기능 자체를 보류한 상태. 자동으로 다시 도는 스케줄/트리거가 있는지 이번에 재확인했고, 없음을 확인함(아래 12번 참고와 별개로 이 기능 자체가 안 켜져 있음)
- DB: `translations` 테이블 **477건 (전체 완료)**. 2026-09-07 3건 라이브 검증 후 나머지 474건에 대해 `TRANSLATOR_ENGINE=openai`로 전체 배치를 백그라운드 실행 → 2026-09-08 사용자 요청으로 399건에서 중간 정지 → 2026-09-11 남은 78건에 대해 배치를 재개해 완료(`run_translation_batch()` 반환값 78, 실패 0건). `articles.status='COLLECTED'`(미번역) 0건 확인 — 전체 477건 번역 완료 상태
- 환경 확인: `argostranslate` 패키지가 이 환경엔 원래 설치돼 있지 않았음(2026-09-07 직접 설치 후 테스트 실행). 설치 후에도 **Argos 오프라인 언어 모델 자체는 설치되어 있지 않음**(`argostranslate.package.get_installed_packages()` → 빈 배열) — 즉 `setup_argos_model.py`가 이 환경에서 실행된 적이 없어서, `ENGINE="argos"`(현재 기본값)로 지금 당장 `translate.py`를 돌리면 실제 번역은 실패함. `ENGINE="openai"`(아래 참고)는 실제로 성공 확인됨
- OpenAI 엔진 라이브 검증(2026-09-07): DB에서 실제 `COLLECTED` 기사 3건(id 1/2/3, The Anfield Wrap 팟캐스트 요약 기사)을 뽑아 `translate.ENGINE="openai"`로 `translate_article()` → `db.save_translation()`까지 실제로 실행. **3건 모두 성공**, `model_version="gpt-5-mini"`로 저장됨. (첫 시도는 `.env`의 `OPENAI_API_KEY`에 예전 Anthropic 키가 잘못 들어있어 401로 3건 모두 실패했었고, 사용자가 키를 수정한 뒤 재시도해 성공함)
  - 품질 주관 평가: 3~5문장 요약이 자연스럽고 사실관계(인명 Neil Atkinson/Andoni Iraola, 스코어 "리버풀 2-2 노팅엄 포레스트" 등) 정확하게 유지됨. 원문을 그대로 베끼지 않고 재구성된 요약이라 저작권 규칙에도 부합. Argos(직역투, 요약 없음)보다 자연스럽고, 기존 Claude(claude-opus-5) 엔진과 비슷한 구조의 요약형 출력을 냄(직접 비교 실행은 안 함). 다만 사람 이름 표기 하나("Rob Gutmann"→"롭 굿맨")가 일반적인 표기("구트만" 등)와 다르게 음역된 사례가 있어, 고유명사 표기 정확성은 대량 실행 전 추가 표본 검토가 필요해 보임
- 테스트: `translator/tests/` 59개(anthropic 3 + argos 4 + openai 9 신규 포함) — `argostranslate`/`openai` 설치 후 전부 통과(단, 이 테스트들은 mock 기반 단위 테스트이고, 실제 API 성공 여부는 위 라이브 검증으로 별도 확인함)

### 12. translator 자동 실행 여부 (참고 — 배치 자동화)

**✅ 완료** (커밋 `31e82c5`, 2026-09-12 — 작업 자체는 2026-09-11) — 2026-09-06/07 확인 시점엔 "자동화가 없다"였으나, 2026-09-11 세션에서 연결함

- 코드: `collector/scheduler.py`의 `run_collection_and_translation_job()`이 `run_collection_job()`(RSS 수집) 직후 `run_translation_job()`을 이어서 실행하도록 변경(30분 간격 스케줄에 그대로 적용됨, 시작 시 1회 즉시 실행도 포함). collector와 translator는 별도 모듈이라(각자 `db.py`를 따로 관리, 이름이 같아 같은 프로세스로 import하면 충돌) 같은 프로세스로 합치지 않고 `subprocess.run(["python", "translate.py"], cwd=translator/)`로 분리 실행
- 번역 엔진: `TRANSLATOR_ENGINE` 환경 변수를 따르며 지정 없으면 `openai` 기본값(이 환경엔 Argos 오프라인 모델 미설치 — 11번 참고). 실패해도(네트워크 오류, API 키 누락 등) 예외를 던지지 않아 수집 스케줄러 자체는 멈추지 않고 다음 30분 주기에 재시도됨
- Windows 작업 스케줄러/cron 등록은 여전히 없음 — `python scheduler.py`를 직접 실행 중인 동안에만 동작한다(그 프로세스가 살아있는 동안 30분 간격 반복). 서버 재부팅 시 자동 시작되지 않으므로, 정말 상시 자동화하려면 별도로 Windows 작업 스케줄러/서비스 등록이 필요함(아직 안 함)
- 테스트: `collector/tests/test_scheduler.py`에 `run_translation_job`/`run_collection_and_translation_job` 관련 5개 추가(서브프로세스 호출은 mock 처리, 실제 실행은 안 함) — 전부 통과
- 확인일: 2026-09-11

### 13. collector 소스 목록 (RSS)

**✅ 완료** (커밋 `c443e2e`, 2026-09-04, 이후 소스 조사 내용은 `collector/sources.py` 주석에 계속 누적)

| 소스 | source_tier | forced_club | 비고 |
|---|---|---|---|
| The Anfield Wrap | 2 | Liverpool | 이미지 메타데이터 없음(확인됨) |
| Empire of The Kop | 3 | Liverpool | |
| Anfield Watch | 3 | Liverpool | 이미지 메타데이터 없음(확인됨) |
| Sky Sports Football | 1 | (자동 감지) | |
| Independent Football | 1 | (자동 감지) | |
| Football365 | 2 | (자동 감지) | |
| 90min | 2 | (자동 감지) | RSS 항목이 항상 발행일순은 아님(`sources.py` 주석) |
| TeamTalk | 2 | (자동 감지) | 2026-09-11 추가. `teamtalk.com/rss` 실제 RSS 확인, robots.txt에 AI 봇 차단 없음 |
| Planet Football | 2 | (자동 감지) | 2026-09-11 추가. `planetfootball.com/feed/` 표준 워드프레스 RSS, robots.txt에 AI 봇 차단 없음 |

`source_tier`: 1=공식/대형 매체, 2=자체 취재하는 전문 매체, 3=팬 블로그 성격. robots.txt/AI 크롤러 차단 문구를 확인 후 제외한 후보(BBC, Guardian, ESPN, Marca, Football Italia, talkSPORT, Metro, Liverpool Echo — 2026-09-04 조사/ GiveMeSport, football.london, Mirror Football, CaughtOffside, FootballTransfers.com — 2026-09-11 조사)도 `sources.py` 주석에 근거와 함께 기록되어 있음.

### 14. 기사 수집량 확대 (백필 페이지 확장 + 신규 소스)

**✅ 완료** (커밋 `92dd94d`, 2026-09-12 — 작업 자체는 2026-09-11)

- 작업: `collector/backfill.py --pages 8`를 소스 9곳 전체(기존 7곳 + 신규 2곳)로 실행해 과거 아카이브를 더 깊이 수집. `REQUEST_DELAY_SECONDS`(1.5초)는 그대로 유지
- 신규 소스 조사(2026-09-11, 후보 7곳: GiveMeSport/TeamTalk/football.london/Mirror Football/CaughtOffside/FootballTransfers.com/PlanetFootball) — **추가**: TeamTalk, PlanetFootball(둘 다 실제 RSS 확인 + robots.txt에 AI 봇 차단 문구 없음). **제외**: GiveMeSport(robots.txt가 AI 학습/RAG용 사용을 명시적으로 전면 금지 + anthropic-ai/ClaudeBot 개별 차단), football.london·Mirror Football(Reach plc 소유, 이미 제외한 Metro/Liverpool Echo와 동일하게 ClaudeBot/anthropic-ai를 `Disallow: /`), CaughtOffside(robots.txt가 링크하는 `m4ow.uk/socw/2.txt`가 Football Italia와 동일한 "Search Only Terms Contract"로 AI 데이터셋 구축을 전면 금지), FootballTransfers.com(`/rss`·`/en/feed`가 실제로는 RSS가 아니라 SPA 홈페이지 HTML을 그대로 반환 — RSS 자체가 존재하지 않아 기술적으로 등록 불가). 근거 상세는 `collector/sources.py` 주석 참고
- DB 반영: 백필 전 477건 → 백필 후 **847건**(신규 370건, 원문 수집 시점 raw 항목 1577건 중복 제외). 소스별 분포는 위 13번 표 및 아래 DB 스냅샷 참고
- 테스트: 별도 테스트 파일 없음(기존 `backfill_categories.py` 등 다른 1회성 배치 스크립트와 동일한 컨벤션) — `max_pages`/`delay_seconds` 페이지네이션 로직 자체는 `collector/tests/test_rss_collector.py`가 이미 검증

### 15. 상세 페이지 본문 이미지 (크롤링 + 표시)

**✅ 완료** (커밋 `d26e2b9`, 2026-09-12 — 작업 자체는 2026-09-11)

- 코드: `collector/body_image_extractor.py`(신규) — 기사 원문 페이지를 요청해 본문 컨테이너(`<article>` 등 우선순위 셀렉터) 안의 `<img>` 태그를 추출. 광고/공유버튼/아바타/로고/테마 배지/팀 엠블럼 아이콘/도박 책임 고지 배너는 URL·클래스명 패턴으로, "관련 기사 추천"·"뉴스레터 팔로우 유도" 같은 사이트 위젯은 조상 요소의 클래스명(`sdc-article-strapline`, `sdc-site-tile` 등 실제 Sky Sports 사례로 확인)으로, 배너/아이콘류는 width/height 비율로 각각 걸러낸다. 지연 로딩 플레이스홀더(data: URI 1x1 GIF)는 `data-src`로 대체 추출. 이미지 파일 자체는 다운로드/재호스팅하지 않고 URL만 저장(저작권 원칙 동일)
- DB: `article_images` 테이블 신규(`article_id`+`position` 복합 PK, `docs/DB_SCHEMA.md` 참고). `collector/db.py`의 `save_articles()`가 신규 기사 저장 시마다 자동 크롤링(요청 간 1초 지연, `BODY_IMAGE_REQUEST_DELAY_SECONDS`). 기존 기사용 소급 배치 `collector/backfill_article_images.py`(신규)
- 실행 결과(2026-09-11): 전체 847건 중 **769건(91%)에서 본문 이미지 확보**, 총 1021개 row. 실행 도중 실제 라이브 데이터에서 이미지 오추출 버그 4종을 발견해 수정: (1) 지연 로딩 플레이스홀더가 "이미지"로 잘못 추출(theanfieldwrap.com), (2) PlanetFootball/Football365/TeamTalk 세 곳이 공유하는 테마의 "Google 뉴스 선호 소스" 배지 이미지가 본문 이미지로 오인(3개 사이트 동일 테마 확인), (3) Sky Sports의 WhatsApp 팔로우 유도·Super 6 배팅 홍보·"관련 기사 더 보기" 추천 그리드가 `<article>` 태그 안에 포함돼 있어 오추출, (4) Football365 기사 본문에 삽입된 도박 책임 고지 배너(gambleaware.org 링크, 1600x200 배너). 네 경우 모두 발견 시점에 오염된 DB row를 정리하고 재크롤링해 반영함
- 백엔드: `Article.images`(`@ElementCollection` + `@OrderColumn`), `ArticleDetailResponse.images`, `ArticleService`가 상세 조회 시 함께 반환(`docs/API.md` 참고)
- 프론트엔드: `ArticleDetailPage.jsx` 상단에 대표 이미지(본문 크롤링 이미지 최우선, 없으면 RSS 썸네일 `imageUrl`로 폴백), 본문 문단 사이에 최대 2장 추가 삽입(`splitIntoParagraphs`로 문단 분리 후 균등 배치), 이미지 로드 실패 시 자동 숨김(기존 썸네일 폴백 로직과 동일). **설계 결정(2026-09-11, 사용자 피드백 반영)**: 처음엔 `imageUrl`을 항상 우선했으나, Sky Sports "Paper Talk" 같은 매체 브랜드 템플릿 그래픽이 대표 이미지로 뜨는 문제가 실제 확인되어 본문 크롤링 이미지(실제 선수/경기 사진일 가능성이 높음)를 우선하도록 뒤집음 — `imageUrl`은 본문 이미지가 하나도 없을 때만 폴백으로 사용
- 알려진 한계: 브랜드 템플릿 썸네일 오탐 방지 로직들은 실제 발견된 사례 기반 휴리스틱이라 완벽하지 않음. "Paper Talk"류 텍스트 요약 기사나 하이라이트 영상 임베드 기사는 애초에 본문에 실제 사진이 없어(비디오 썸네일이나 매체 브랜드 그래픽만 있음) 개선의 여지가 없는 경우도 있음(소스 콘텐츠 자체의 한계, 콜렉터 로직 문제 아님)
- 테스트: `collector/tests/test_body_image_extractor.py`(24개, 위 4가지 실제 버그 각각에 대한 회귀 테스트 포함), `collector/tests/test_db.py`(이미지 저장/폴백 2개 추가), 백엔드 `ArticleRepositoryTest`(1개 추가), 프론트 `articleDisplay.test.js`(`splitIntoParagraphs` 5개), `ArticleDetailPage.test.jsx`(신규 파일, 6개) — 전부 통과
- 브라우저 실측 확인(2026-09-11): 이미지 있는 기사(대표 이미지만 있는 경우, 문단 사이 삽입까지 있는 경우)와 없는 기사 각각 레이아웃 깨짐 없이 정상 표시 확인. 사용자가 실시간으로 Sky Sports 브랜드 로고 노출 문제를 지적해 즉시 수정 및 재확인함

---

## 테스트 스위트 전체 결과 (2026-09-12 재실행 기준, 커밋 전 최종 확인)

| 모듈 | 결과 | 비고 |
|---|---|---|
| backend (`./gradlew test --rerun`) | ✅ BUILD SUCCESSFUL | ⚠️ 이 프로젝트는 `build.gradle`에서 빌드 출력을 `%TEMP%/liverpool-news-backend-build`로 리다이렉트함(OneDrive 동기화 문제 회피) — `backend/build/`(프로젝트 폴더 안)의 결과는 stale 데이터이니 참고하지 말 것 |
| collector (`pytest tests/`) | ✅ 155개 테스트, 0 실패 | 2026-09-11 세션 기록엔 150개였으나 재실행 시 155개로 집계됨(카운트 오차, 실패 아님) |
| translator (`pytest tests/`) | ✅ 59개 테스트, 0 실패 (2026-09-07 기준, 이번 세션엔 변경 없음) | |
| frontend-web (`vitest run`) | ✅ 11개 파일, 50개 테스트, 0 실패 | |

## DB 현재 상태 스냅샷 (2026-09-11, 로컬 MySQL80 `footballnews`)

| 테이블/항목 | 값 |
|---|---|
| articles | 847건 (2026-09-07엔 477건 — 위 14번 백필 확대 참고) |
| article_clubs | 981행 |
| article_images | 1021행 (본문 이미지 있는 기사 769건 / 847건, 91% — 위 15번 참고) |
| articles.quoted_reporter 채워짐 | 확인 안 함(이번 세션 미변경 영역) |
| articles.image_url 채워짐 | 확인 안 함(이번 세션 미변경 영역, 백필로 신규 370건 추가되며 수치 자체는 변함) |
| rumor_threads / rumor_thread_articles | 확인 안 함(이번 세션 미변경 영역, 백필로 신규 기사 유입되며 수치는 변함) |
| users | 1건 |
| user_preferences | 1건 (favorite_club_id 설정 0건) |
| translations | 478건 (2026-09-11 테스트로 1건 추가 번역 — 위 15번 참고. 신규 백필 370건은 대부분 미번역 상태) |
| clubs | 50건 |
