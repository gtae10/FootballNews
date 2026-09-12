# 기능 구현 현황

이 문서는 코드/DB/테스트를 실제로 대조해 확인한 "사실"만 기록합니다. 추측이나 계획은 넣지 않습니다.

**확인 시점**: 2026-09-11 (최초 작성 2026-09-07). **확인 방법**: git 커밋 로그, 로컬 MySQL80(`footballnews` DB) 직접 조회, 각 모듈 테스트 스위트 실행(백엔드 `./gradlew test`, collector/translator `pytest`, 프론트 `vitest run`), 일부는 실제로 서버를 띄워 브라우저로 확인.

**새 세션을 시작하기 전에 이 문서를 먼저 읽으세요.**

> **갱신 이력**: 2026-09-07 최초 작성 시점엔 최애팀/카테고리 분류가 미커밋 상태였으나, 같은 날 커밋 `d362233`(카테고리 분류), `93ee6ca`(최애팀), `c89dbde`(이 문서 자체)로 커밋 완료됨. 아래 4/8번 항목은 이 커밋 반영 후 내용임. 2026-09-11 세션에서 번역 배치 재개 완료(11번), 기사 수집량 확대(14번, 신규), 상세 페이지 본문 이미지(15번, 신규)를 추가했고, 그 세션 작업분은 미커밋 상태로 남아있었음. 2026-09-12 세션 전반부에서 전체 테스트 재확인(백엔드 54개/collector 155개/프론트 50개, 전부 통과) 후 커밋 완료: `a1b9d05`("433" 리브랜딩), `31e82c5`(12번 스케줄러 자동연결), `92dd94d`(14번 소스 확대), `d26e2b9`(15번 본문 이미지). 같은 세션 후반부에서 UI 개편(전체/관심구단 탭 분리, 폰트 크기, 반응형) 작업 — 아래 16번 항목 신규, **미커밋 상태**.

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
- **2026-09-12 세션 진단 + 보강**: 50개 구단 중 기사 0건인 구단 23개 발견(전부 분데스리가/라리가/리그1/세리에A의 중위권 구단 — EPL·빅클럽은 전부 1건 이상). 5개 이상 표본으로 원인 조사: (1) `Real Betis`는 실제로 "Betis" 축약형으로 언급된 기사(id 810, Planet Football)가 이미 있었는데 `club_matcher.ALIAS_OVERRIDES`에 별칭이 없어 놓치고 있었음(**진짜 매칭 버그, 수정함** — `"Real Betis": ["Betis"]` 추가) (2) `Union Berlin`은 "Union Saint-Gilloise"(벨기에 다른 구단)와 혼동될 뻔했으나 기존 구단명 전체 매칭 로직이 이미 정확히 구분하고 있어 버그 아님(진짜 0건) (3) 나머지 21개는 텍스트 검색으로도 어떤 표현으로도 언급 자체가 없어 **소스 자체의 한계**(영어권 매체가 이 리그 중위권 구단을 잘 안 다룸)로 판단
  - `retag_articles.py`에 `--all` 플래그 추가(`retag_all_articles_for_new_aliases`, 신규): 기존 `retag_untagged_articles`는 태그가 하나도 없는 기사만 보는데, "Betis" 같은 새 별칭은 이미 다른 구단(AS Roma)으로 태깅된 기사에도 적용돼야 해서 전체 기사를 다시 스캔하는 버전이 필요했음. 실행 결과 Real Betis 외에도 별칭 맵이 그동안 여러 커밋에 걸쳐 갱신되면서 쌓여 있던 태깅 누락(Everton/Manchester City/Chelsea 등 기존 구단들도 일부 기사에서 추가로 태깅됨, +17건)이 함께 해소됨
  - 백필 확대(8→15페이지, 아래 14번 참고) 후 재확인: 0건 구단 23 → **20개**로 감소(Real Betis 외에 Lens/Lille은 별칭 문제가 아니라 백필로 새로 수집된 기사에 있었음). 나머지 20개는 확대된 전체 1321건 기준으로도 텍스트 검색 0건 재확인 — 소스 한계로 최종 판단(목록: Bayer Leverkusen, Borussia Monchengladbach, Eintracht Frankfurt, Freiburg, Union Berlin, Wolfsburg, Athletic Bilbao, Girona, Real Sociedad, Sevilla, Villarreal, Lyon, Marseille, Strasbourg, Toulouse, Atalanta, Bologna, Fiorentina, Lazio, Torino)
  - 브라우저/API 확인: `GET /articles?club=Real Betis`, `club=Lille`, `club=Lens` 모두 정상 반환 확인
  - 테스트: `test_club_matcher.py`에 Real Betis 축약형 매칭 1개, `test_retag_articles.py`에 전체 재태깅(기존 태그 있는 기사에 추가 태깅 + 멱등성) 2개 추가 — collector 전체 164개 통과

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
- **2026-09-12 세션 추가 작업**: 백필(14번)로 쌓인 미번역 59건을 `TRANSLATOR_ENGINE=openai`로 재실행 → 59건 전부 성공, `articles.status='COLLECTED'` 0건(전체 847건 번역 완료) 재확인. 이 과정에서 **버그 발견**: `content_original`이 빈 문자열인 기사(21건, 전부 Sky Sports Football — 대부분 `/live-blog/` 페이지로 RSS `summary` 필드 자체가 비어 있었음)에 대해 기존 `translate_article()`이 그대로 엔진을 호출하고 있었고, 그 결과 OpenAI 엔진이 (a) 6건은 "본문이 없어 요약할 수 없다"는 정직한 거부 응답을, (b) **15건은 제목만 보고 그럴듯한 내용을 지어낸 요약(할루시네이션)**을 반환해 `content_ko`에 그대로 저장돼 있었음(`docs/LEGAL_NOTES.md`의 "원문 기반 요약" 원칙 위반). `translate_article()`에 `content_original`이 공백이면 엔진 호출 없이 바로 `ValueError`를 던지는 가드를 추가(`run_translation_batch()`의 기존 실패 처리 경로를 그대로 타서 status는 COLLECTED로 유지)하고, 오염된 21건은 `translations` row 삭제 + status를 COLLECTED로 되돌린 뒤 재실행 → 이번엔 API 호출 없이 21건 전부 정상적으로 스킵됨(현재 `articles.status`: TRANSLATED 826 / COLLECTED 21). 프론트는 번역 없는 기사에 대한 기존 폴백(원문 제목 + "번역이 아직 준비되지 않았습니다" 안내)이 이미 있어 추가 프론트 변경은 없었음(브라우저로 확인, id 676)
  - 테스트: `translator/tests/test_translate.py`에 2개 추가(`translate_article`이 빈/공백/None `content_original`에서 엔진 호출 없이 예외를 던지는 것, `run_translation_batch`가 그런 기사를 건너뛰고 나머지는 계속 처리하는 것) — 전체 63개 통과
  - 남은 한계였음 → **바로 이어서 크롤링 시도함**: `collector/body_text_extractor.py`(신규, `body_image_extractor.py`와 동일한 본문 컨테이너 셀렉터 재사용) + `collector/backfill_missing_content.py`(신규, 1회성 배치)로 21건 전부에 대해 원문 페이지 본문 크롤링 시도. 결과: **일반 뉴스 기사 3건(423/427/676)은 본문 확보 성공**(각 6072/13780/6774자, `status`는 COLLECTED로 유지해 다음 번역 배치 대상), **라이브 블로그/라이브 매치 페이지 18건은 실패** — 원인은 크롤링 로직 문제가 아니라 Sky Sports가 만료된 라이브 블로그에 실제 본문 대신 `"Sorry, this blog is currently unavailable."` 플레이스홀더만 내려주는 것으로 직접 확인함(정적 HTTP 요청으로 확인, JS 렌더링 이슈 아님) — 소스 자체의 한계로 판단, 더 시도하지 않음
  - 테스트: `collector/tests/test_body_text_extractor.py`(신규, 6개) — 정상 추출/바이라인·타임스탬프 노이즈 필터링/라이브 블로그 만료 감지/컨테이너 없음/너무 짧음/요청 실패 케이스. collector 전체 161개 통과
  - 자동화 제안(실행 안 함, 사용자 판단 대기): `collector/scheduler.py`는 이미 수집 직후 번역 배치를 자동 실행하도록 연결돼 있음(12번 참고)이지만 `collector/backfill.py`(일회성 대량 수집 스크립트)는 번역 호출이 전혀 없어, 백필 실행 후 번역이 계속 밀리는 패턴의 원인으로 보임 — backfill 실행 끝에 번역 배치를 이어 호출하는 옵션을 제안했으나 번역 API 비용 문제로 사용자가 자동 연결 여부를 아직 결정하지 않음
- **2026-09-12 세션 3차 실행**: 구단 매칭 보강 + 백필 확대(위 5/14번 참고)로 새로 쌓인 미번역 495건에 대해 `TRANSLATOR_ENGINE=openai`로 재실행 → **477건 성공, 18건은 위 body_text_extractor로도 못 채운 만료 라이브 블로그라 가드가 정상적으로 스킵**(API 호출 없음, 실패 아님). 최종 `articles.status`: TRANSLATED **1303** / COLLECTED **18**(1321건 중 98.6%). README용 스크린샷을 이 번역 완료 상태로 다시 촬영함(`docs/screenshots/`)

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
- **2026-09-12 세션 2차 확대(8→15페이지)**: 847건 → **1321건**(신규 474건, raw 2925건 중 중복 제외). 소스별: Anfield Watch 300 / The Anfield Wrap 225 / Empire of The Kop 225 / Football365 151 / Planet Football 148 / 90min 90 / Sky Sports Football 65 / Independent Football 65 / TeamTalk 52. **버그 발견 및 수정**: 이 실행 시 백엔드가 기본 포트(8080)가 아니라 8081에서 떠 있었는데, `collector/db.py`의 `_load_alias_map()`이 `GET /clubs`를 기본 URL(`http://localhost:8080`)로 호출하다 실패해 신규 474건 중 forced_club이 없는 소스(Sky Sports/Independent/Football365/90min/TeamTalk/Planet Football) 307건이 구단 태깅 없이 저장됨(실패는 조용히 무시되고 로그 한 줄만 남기는 기존 설계 — `db.py` 자체는 정상 동작, 이번엔 환경(포트 충돌) 문제). `COLLECTOR_BACKEND_API_URL` 환경변수로 올바른 포트를 지정해 `retag_articles.py --all`을 재실행해 307건 전부 재태깅함(결과는 위 5번 항목 참고). **주의**: 로컬에서 collector 스크립트를 백엔드가 기본 포트가 아닌 곳에 떠 있는 상태로 실행할 때는 `COLLECTOR_BACKEND_API_URL`을 반드시 맞춰줘야 함
- 테스트: 이번에도 별도 테스트 파일 없음(기존 컨벤션과 동일, 페이지네이션 로직은 기존 테스트가 커버)

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

### 16. UI 개편 (전체/관심구단 탭 분리, 폰트 크기, 반응형)

**✅ 완료** (미커밋, 2026-09-12)

- 앱 이름 표시: 남아있던 마지막 "리버풀 뉴스" 문구(`FeedPage.jsx` 헤더 워드마크)를 "433"으로 교체 — 나머지(로그인 페이지, README, index.html 타이틀)는 이전 세션에서 이미 완료돼 있었음. 백엔드 패키지명/폴더명은 범위 밖으로 유지(사용자 확인 사항, 변경 없음)
- **전체/관심구단 탭 분리 — 버그 수정**: 기존엔 로그인 사용자가 피드에 들어오면 "전체"를 눌러도 관심 구단 중 첫 번째로 club 필터가 자동으로 걸려 있는 버그가 있었음(`FeedPage.jsx`가 로그인 시 `preference.clubs[0]`으로 필터를 초기화했었음). 이번에 탭 상태(`activeTab: "all" | "interests"`)를 도입해 완전히 분리:
  - "전체" 탭: club 필터 없이 전체 구단 기사(카테고리 필터는 그대로 적용). 기존 구단 드롭다운은 "전체" 탭 안의 보조 필터로 유지(`allClubFilter` 상태, 관심구단 로직과 독립)
  - "관심구단" 탭: 로그인 사용자의 관심 구단으로 필터링. 서브필터 "관심 구단 전체"(백엔드 `clubs` 콤마구분 파라미터로 다건 조회 — `ArticleRepository.searchByClubs`, 이미 구현/테스트돼 있던 것을 프론트에서 처음 실사용) vs "최애팀만"(`club` 단일 파라미터). 관심 구단/최애팀이 비어있으면 설정 페이지로 유도하는 안내 문구 표시
  - 게스트가 "관심구단" 탭을 누르면 로그인 유도 링크만 보이고 기사 조회 자체를 하지 않음(`/users/me/preferences` 호출 안 함)
  - `FavoriteTeamSection`의 "더보기" 클릭은 "전체" 탭 + 구단 드롭다운으로 이동하도록 변경(기존 동작과 동등)
  - 실브라우저 확인(2026-09-12): 실제 계정(관심 구단 1개: Liverpool, 최애팀 미설정)으로 로그인 상태에서 "전체" 탭이 Arsenal/Man City/Man Utd/Tottenham/Atletico Madrid/Barcelona 등 여러 구단 기사가 실제로 섞여 나오는 것을 확인(버그 수정 확인). "관심구단" 탭 → "최애팀만"에서 최애팀 미설정 안내 문구가 뜨는 것도 확인. "전체" 탭의 구단 드롭다운에서 Chelsea를 선택하면 Chelsea 기사만 정확히 좁혀지는 것도 확인. `clubs=` 콤마구분 다건 조회 자체는 백엔드 `ArticleRepositoryTest`(기존 테스트)와 프론트 단위 테스트로 검증(이 계정은 관심 구단이 1개뿐이라 브라우저에서 다건 케이스 자체는 직접 재현하지 못함)
- 폰트 크기: 헤더 워드마크(`.rf-wordmark`) 12px → 16px(+ font-weight 700). 기사 카드/상세 페이지/오늘의 주요 소식의 티어 뱃지("T1 공식 발표" 등) 10.5px → 12.5px. 제목(17.5~31px) > 본문(16px) > 메타정보 위계는 그대로 유지
- 반응형: 기존엔 미디어 쿼리가 전혀 없었음. `max-width: 600px` 브레이크포인트 하나로 대응 — 검색줄(`rf-search-row`)이 좁은 화면에서 줄바꿈(키워드 입력 전체 폭, 구단 드롭다운+검색 버튼이 둘째 줄), 기사 카드 썸네일 96px→72px, 기사 제목/상세 제목 폰트 축소. 탭/카테고리 칩은 기존에 이미 `flex-wrap`이라 별도 처리 불필요. 상세 페이지 이미지는 기존에 이미 `width:100%`라 별도 처리 없이도 반응형이었음(확인만 함)
  - 실측 확인(2026-09-12): 실제 리사이즈 도구(`resize_window`)가 이 환경에서 실제 뷰포트에 반영되지 않아(window.innerWidth가 그대로 유지됨을 확인) 페이지 안에 `<iframe>`을 주입해 375px/1280px 폭을 직접 만들어 스크린샷으로 확인하는 방식을 썼음. 375px에서 가로 스크롤 없이 탭/칩 줄바꿈, 검색줄 2줄 분리, 썸네일 축소, 상세 페이지 히어로 이미지 컨테이너 폭 맞춤(316px, 컨테이너 안에 들어옴)을 확인. 1280px에서는 기존 데스크톱 레이아웃(`max-width:720px` 중앙 정렬)이 그대로 유지됨을 확인
- 테스트: `frontend-web` 프론트 테스트 12개 추가/수정(`FeedPage.test.jsx`) — 기본 탭이 "전체"라 로그인 사용자도 club 파라미터 없이 조회하는 회귀 테스트, 관심구단 탭 클릭 시 `clubs=` 다건 조회, "최애팀만" 서브필터 시 `club=` 단건 조회, 게스트가 관심구단 탭에서 로그인 안내만 보고 조회하지 않는 것 — 전부 통과(프론트 전체 스위트 54개 재실행 기준)
- 남은 이슈였음 → **커밋 완료**: 2026-09-12 세션 후반부에 커밋 `4034380`으로 반영됨

### 17. RSS 제목/본문 HTML 엔티티 이중 인코딩 정리

**✅ 완료** (커밋 `dd7a349`, 2026-09-12)

- 문제 발견 경위: README 스크린샷을 찍으려고 피드 페이지를 열었다가 "Romano reveals &#8216;important moment&#8217;..."처럼 제목에 글자 대신 HTML 엔티티 코드가 그대로 노출되는 것을 실제로 확인함
- 원인: 일부 워드프레스 계열 RSS가 엔티티를 이중 인코딩해서 내려주는데(`&amp;#8217;` → XML 파싱 후 `&#8217;`), `collector/rss_collector.py`가 `feedparser`의 1차 파싱 결과를 그대로 `title_original`/`content_original`에 저장해 2차 디코딩이 안 되고 있었음
- 코드: `rss_collector.py`의 `collect_from_rss()`가 저장 시점에 `html.unescape()`(stdlib)를 한 번 더 적용하도록 수정
- DB: `collector/backfill_unescape_titles.py`(신규, 1회성 배치)로 기존 저장분 소급 정리 — **1321건 중 709건**(약 54%)이 이 문제를 갖고 있었음, 전부 수정
- 테스트: `collector/tests/test_rss_collector.py`에 이중 인코딩 디코딩 회귀 테스트 1개 추가 — collector 전체 165개 통과
- 알려진 한계: 이미 번역 완료된 기사의 한국어 요약(`content_ko`)은 재번역하지 않음(비용 문제) — 영어 원문(`title_original`/`content_original`)은 깨끗해졌지만, 그 이전에 생성된 한국어 번역 결과 자체에 엔티티 잔재가 섞여 있었다면 그대로 남아있을 수 있음(표본 확인 결과 번역 과정에서 LLM이 대부분 자연스럽게 처리해 실제 영향은 적어 보였음)

### 18. 스케줄러 상시 실행 중 발견한 버그 2건 (cp949 디코딩 에러, 백엔드 의존성)

**✅ 완료** (커밋 `f1c80e3`, 2026-09-12)

- 배경: 사용자 요청으로 `collector/scheduler.py`를 30분 주기 상시 백그라운드 프로세스로 처음 실행했는데, 실행 중 실제 에러 2건을 발견함
- **버그 1 — 번역 서브프로세스 출력 디코딩 실패**: `run_translation_job()`이 `subprocess.run(["python", "translate.py"], ..., text=True)`로 자식 프로세스를 실행하는데, `encoding`을 지정하지 않아 한국어 Windows의 기본 코드페이지(cp949)로 디코딩을 시도 — 자식은 UTF-8로 출력하므로 `UnicodeDecodeError`가 발생(`Exception in thread Thread-1 (_readerthread)`로 로그에 남음). **실제 영향 조사 결과: 데이터 손실은 0건.** 이 에러는 subprocess 내부 리더 스레드에서 나서 부모 프로세스(scheduler.py)로 전파되지 않고, 자식 프로세스(translate.py) 자체는 끝까지 정상 실행되어 DB에 번역 결과를 그대로 저장함 — 실제로 이 사건이 벌어진 사이클에서 신규 기사 27건 중 21건이 정상 번역·저장된 것을 DB로 확인함(나머지 6건은 버그와 무관하게 `content_original`이 비어 있어 가드가 정상적으로 건너뜀). 즉 이 버그의 실질적 영향은 "스케줄러 자체 로그에 결과가 안 남고 트레이스백만 남는다"는 가시성 문제였지 데이터 유실이 아니었음
  - 수정: `subprocess.run(...)`에 `encoding="utf-8"` 명시
  - 테스트: `collector/tests/test_scheduler.py`에 1개 추가 — collector 전체 통과
- **버그 2 — 백엔드가 안 떠 있으면(또는 다른 포트에 떠 있으면) 구단 자동 태깅이 스킵됨**: `collector/club_matcher.py`의 `fetch_clubs()`가 백엔드 `GET /clubs`를 HTTP로 호출했는데, 실패하면 `db.py`의 `_load_alias_map()`이 예외를 잡고 빈 맵을 반환해 본문 기반 구단 감지 자체가 전부 스킵됐음(로그에 한 줄만 남아 눈에 띄기 어려움). 이 세션 중 실제로 두 차례 발생(2026-09-11 백필, 2026-09-12 백필 — 둘 다 이미 발견해 `retag_articles.py --all`로 복구한 바 있음, 위 5/14번 참고)
  - **구조적 수정**: HTTP 호출을 아예 없애고 `club_matcher.fetch_clubs_from_db(engine)`(신규)로 `clubs` 테이블을 직접 조회하도록 바꿈 — collector는 어차피 backend와 같은 MySQL을 보고 있어 이 HTTP 의존성 자체가 불필요했다고 판단함(collector가 기사 저장에 쓰는 것과 같은 DB 연결). `db.py`(`_load_alias_map`), `retag_articles.py`, `build_rumor_threads.py` 세 호출부 모두 전환. 이제 collector 배치 작업들은 백엔드(Spring Boot)가 떠 있는지 여부와 완전히 무관하게 동작함 — 백엔드는 프론트엔드가 브라우징할 때만 필요
  - 보조 조치: 그래도 `clubs` 테이블 조회 자체가 실패하는 극단적 경우(예: 스키마 마이그레이션 전)를 대비해 try/except는 유지하되, 기존엔 stdout에 한 줄만 남기던 것을 `[WARNING]` 태그를 붙여 stderr로 남기도록 바꿔 눈에 띄게 함
  - `club_matcher.fetch_clubs()`(HTTP 버전)와 `DEFAULT_BACKEND_API_URL`/`COLLECTOR_BACKEND_API_URL`은 더 이상 쓰는 곳이 없어 완전히 제거함
  - 테스트: `test_club_matcher.py`에 `fetch_clubs_from_db` 1개, `test_db.py`에 `_load_alias_map` 성공/실패(경고 로그 확인) 2개 추가
  - 과거 누락 데이터 재확인(요청 4/5번): `retag_articles.py --all`을 다시 실행 → "재태깅할 기사가 없습니다"(추가로 발견된 누락 없음, 이전 세션에서 이미 다 복구됨을 재확인). 0건 구단 20개(위 5번의 최종 목록과 동일), 태그 없는 기사 203/1348건 — 전부 버그가 아니라 실제로 어떤 추적 구단도 언급하지 않는 기사(리그 전반 이슈 등)로 판단
  - 테스트: collector 전체 169개 통과

### 19. 번역 배치 우선순위 큐 + 하루 처리 한도 (DAILY_TRANSLATION_LIMIT)

**✅ 완료** (커밋 `3728721`, 2026-09-13)

- 배경: 사용자가 "이전에 추가한 DAILY_TRANSLATION_LIMIT"을 언급하며 우선순위 큐를 요청했으나, 실제로는 `DAILY_TRANSLATION_LIMIT`도 요청에서 언급된 `verified_source_count` 컬럼도 코드베이스에 존재하지 않았음(grep 0건 확인) — 실제 컬럼은 `independent_source_count`이고, `docs/DB_SCHEMA.md`에 "의도적으로 `verified_*`가 아닌 이 이름을 썼다"는 설계 의도가 명시돼 있어 그대로 따름. 사용자에게 이 사실을 먼저 알린 뒤, 우선순위 큐와 하루 한도 둘 다 신규 기능으로 구현함
- 코드:
  - `translator/priority.py`(신규): `sort_by_priority()` — 1순위 `source_tier=1` 또는 `quoted_reporter` 존재, 2순위 이적 루머 스레드의 `independent_source_count` 내림차순, 3순위 `published_at` 최신순
  - `translator/db.py`: `fetch_untranslated_articles()`가 우선순위 정렬에 필요한 필드(`source_tier`/`quoted_reporter`/`published_at`/`independent_source_count`, `rumor_thread_articles`/`rumor_threads` LEFT JOIN)까지 함께 조회하도록 확장. `count_translated_today()`(신규) — 오늘(UTC 자정 기준) 이미 처리한 건수를 매번 DB에서 다시 세어 반환(scheduler.py가 30분마다 새 프로세스로 실행되므로 메모리 상태 공유 불가)
  - `translator/translate.py`: `DAILY_TRANSLATION_LIMIT`(기본 300)·`CARRYOVER_WARNING_THRESHOLD`(기본 500) 환경변수 추가. `run_translation_batch()`가 우선순위 정렬 → 오늘 남은 한도만큼만 슬라이스 → 처리, 끝나면 `"오늘 처리: N건, 이월: M건 (엔진: ...)"` 로그 + 이월이 임계값 초과 시 `[WARNING]` 로그. 로그는 scheduler.py 경유 시 그 로그 파일에 그대로 남음(별도 파일 안 만듦)
- **실전 검증(요청 8번)**: 프로덕션 DB에서 서로 다른 우선순위를 가진 기존 번역 완료 기사 7건(tier1 2건/교차검증 2건(count 2·1)/일반 3건)을 골라 번역 row 삭제 + status를 COLLECTED로 되돌린 뒤, `DAILY_TRANSLATION_LIMIT`을 (그날 UTC 기준 이미 처리된 건수 + 29)로 맞춰 실제 `translate.py`를 실행. **예측한 순서(tier1 2건 → 교차검증 2건(count 내림차순) → 일반 중 최신 1건) 그대로 처리되고, 일반 기사 중 가장 오래된 2건은 COLLECTED로 정확히 남는 것을 `translated_at` 타임스탬프로 확인함**. 사용값(한도 등)은 코드에 반영한 게 아니라 이번 실행에만 준 환경변수라 기본값(300)은 그대로 유지됨(되돌릴 것 없음)
  - **부수 발견**: `source_tier=1`은 최우선이라, 본문이 영구히 비어 있는 tier-1 기사(만료된 라이브 블로그 18~24건, 위 11/18번 참고)도 매 배치 큐 맨 앞에서 매번 재시도됨 — API 비용은 안 들지만(빈 본문 가드가 막음) 한도 슬롯을 일부 차지하고 로그에 "번역 실패" 줄이 늘어남. 실제로 이 때문에 한도=5로는 정작 처리할 게 하나도 없어(빈 기사 24건이 전부 소진) 실전 검증 시 한도를 더 크게 잡아야 했음. 코드 수정은 하지 않고 문서에 알려진 상호작용으로 남김
  - 복구: 위 7건 중 5건은 이번 실전 검증으로 정상 재번역됨. 남은 2건(이월분)은 상시 실행 중인 scheduler.py가 다음 30분 주기에 자동으로 다시 처리함 — 수동 복구 불필요(이월 동작 자체를 실제로 보여주는 것이라 의도적으로 그대로 둠)
- 테스트: `translator/tests/test_priority.py`(신규 7개), `test_db.py`(+4), `test_translate.py`(+4), 기존 두 파일의 in-memory DB 픽스처에 `source_tier`/`quoted_reporter`/`published_at`/`rumor_thread_articles`/`rumor_threads` 추가(스키마 확장에 맞춰 갱신) — translator 전체 63 → **78개 통과**

---

## 테스트 스위트 전체 결과 (2026-09-12 재실행 기준, 커밋 전 최종 확인)

| 모듈 | 결과 | 비고 |
|---|---|---|
| backend (`./gradlew test --rerun`) | ✅ BUILD SUCCESSFUL, 58개 | ⚠️ 이 프로젝트는 `build.gradle`에서 빌드 출력을 `%TEMP%/liverpool-news-backend-build`로 리다이렉트함(OneDrive 동기화 문제 회피) — `backend/build/`(프로젝트 폴더 안)의 결과는 stale 데이터이니 참고하지 말 것 |
| collector (`pytest tests/`) | ✅ 169개 테스트, 0 실패 | 이 세션에서 155 → 169(본문 텍스트 크롤링 6, Real Betis 별칭 1, 전체 재태깅 2, HTML 엔티티 디코딩 1, 스케줄러 인코딩 1, DB 직접 조회 3 추가) |
| translator (`pytest tests/`) | ✅ 78개 테스트, 0 실패 | 이 세션에서 59 → 78(본문 없는 기사 가드 2, 우선순위 큐 15 추가) |
| frontend-web (`vitest run`) | ✅ 11개 파일, 54개 테스트, 0 실패 | 16번(UI 개편) 작업으로 `FeedPage.test.jsx`에 4개 추가(50 → 54), 2026-09-12 재실행 기준 |

## DB 현재 상태 스냅샷 (2026-09-12 세션 후반부 기준, 로컬 MySQL80 `footballnews`)

| 테이블/항목 | 값 |
|---|---|
| articles | **1352건** (세션 시작 시점 847건 — 위 14번 2차 백필 확대 + 스케줄러 상시 수집 반영, 계속 증가 중) |
| article_clubs | **1604행** (0건 구단 23 → 20개로 감소 후 안정, 위 5/18번 참고) |
| article_images | 1021행 (2026-09-11 기준, 이번 세션 신규 백필분 474건에는 아직 소급 크롤링 안 함 — 필요 시 `backfill_article_images.py` 재실행 필요) |
| articles.quoted_reporter 채워짐 | 확인 안 함(이번 세션 미변경 영역) |
| rumor_threads / rumor_thread_articles | 확인 안 함(이번 세션 미변경 영역, 백필로 신규 기사 유입되며 수치는 변함) |
| users | 1건 |
| user_preferences | 1건 (favorite_club_id: Liverpool로 설정함 — 이번 세션에서 실사용 데이터 처음 생성, 위 4번 참고) |
| translations | **1323건 완료**, 29건 미번역(`status='COLLECTED'`, 대부분 `content_original` 빈 만료 라이브 블로그 — 본문 확보 불가로 확인됨, 위 11/18번 참고. 그중 2건은 19번의 우선순위 큐 실전 검증에서 의도적으로 이월시킨 것으로 scheduler.py가 곧 자동 처리함) |
| clubs | 50건 |
