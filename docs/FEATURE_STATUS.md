# 기능 구현 현황

이 문서는 코드/DB/테스트를 실제로 대조해 확인한 "사실"만 기록합니다. 추측이나 계획은 넣지 않습니다.

**확인 시점**: 2026-09-07. **확인 방법**: git 커밋 로그, 로컬 MySQL80(`footballnews` DB) 직접 조회, 각 모듈 테스트 스위트 실행(백엔드 `./gradlew test`, collector/translator `pytest`, 프론트 `vitest run`), 일부는 실제로 서버를 띄워 브라우저로 확인.

**새 세션을 시작하기 전에 이 문서를 먼저 읽으세요.** 특히 아래 "⚠️ 커밋되지 않은 완료 기능" 항목은 `git log`만 봐서는 존재를 알 수 없습니다 — working tree(코드 파일)를 직접 확인해야 보입니다.

## ⚠️ 커밋되지 않은 완료 기능 (주의)

**최애팀(favoriteClub)**과 **카테고리 분류(MATCH/TRANSFER/PLAYER/OTHER)** 두 기능은 코드/DB 반영/테스트가 전부 끝났지만 **아직 하나도 커밋되지 않았습니다** (2026-09-07 기준 working tree에만 존재). `git log`로 확인하면 "구현 안 됨"으로 잘못 판단하기 쉬우니, 이 두 기능을 다시 요청받으면 먼저 아래 표를 보고 working tree(`git status`)를 확인하세요.

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

**⚠️ 코드/DB/테스트 전부 완료, 그러나 미커밋** (working tree, 2026-09-06~07 세션에서 확인)

- 코드: `UserPreference.favoriteClub`(Club 다대일 단방향, nullable), `UserPreferenceRequest`/`Response`의 `favoriteClubId`/`favoriteClub`, 온보딩·설정 페이지의 ★ 칩 UI, `FavoriteTeamSection` 컴포넌트(피드 상단, club/category 필터와 무관하게 항상 최애팀 기준 고정)
- 설계 결정: 관심 구단 목록에 없는 구단을 최애팀으로 지정하면 에러 대신 관심 구단에 자동 추가함 (`UserPreferenceService.savePreference` 주석 참고)
- DB: `user_preferences.favorite_club_id` 컬럼 + `clubs.id` FK 제약조건 — 2026-09-06 `./gradlew bootRun` 최초 실행 시 Hibernate가 생성하는 것을 로그로 직접 확인함(그 전까지 이 DB엔 컬럼 자체가 없었음). 실사용 데이터는 아직 0건(최애팀을 설정한 사용자 없음)
- 테스트: 백엔드 `UserPreferenceServiceTest`/`UserPreferenceControllerTest`, 프론트 `FavoriteTeamSection.test.jsx`/`OnboardingPage.test.jsx`/`SettingsPage.test.jsx` — 전부 통과(2026-09-07 재실행: 백엔드 53개, 프론트 39개 중 포함)
- **커밋 없음** — git 커밋 로그로는 이 기능의 존재를 알 수 없음

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
- 참고: `rumor_clusterer.py`는 2026-09-06 카테고리 분류 키워드 보강 작업 때문에 `_STAGE_KEYWORDS`가 추가로 수정됐음(아직 미커밋) — 루머 클러스터링 자체의 신규 기능은 아니고 기존 스테이지 판정 키워드 확장
- DB: `rumor_threads` 18건, `rumor_thread_articles` 21건 연결. **`cross_reported=true`인 스레드는 현재 0건** — 기능 자체는 동작하지만(로직/테스트로 확인됨), 지금 이 DB의 실제 데이터에서는 아직 "48시간 내 2개 이상 매체가 보도"한 사례가 나타나지 않았다는 뜻(결함 아님, 데이터 양이 적어서일 가능성이 높음)
- 테스트: 백엔드 `RumorThreadControllerTest`/`RumorThreadRepositoryTest`, collector `test_rumor_clusterer.py`/`test_build_rumor_threads.py` — 전부 통과(2026-09-07 재실행)

### 8. 카테고리 분류 (MATCH/TRANSFER/PLAYER/OTHER)

**⚠️ 코드/DB/테스트 전부 완료, 그러나 미커밋** (working tree, 2026-09-06 세션에서 확인)

- 코드: `ArticleCategory` enum, `collector/article_classifier.py`(규칙 기반 분류, 우선순위: 루머 스레드 클러스터링 > MATCH 키워드 > PLAYER 키워드 > 미클러스터링 이적 키워드 > OTHER), `collector/category_keywords.py`(MATCH/PLAYER 키워드), `collector/backfill_categories.py`(소급 배치), `collector/db.py`의 `save_articles`가 신규 수집 시점에 자동 분류하도록 연결됨
- DB: `articles.category` 컬럼 — 2026-09-06 최초 `bootRun` 시 Hibernate가 생성(그 전엔 컬럼 없음). 실제 소급 적용 + 키워드 2차 보강 후 최종 분포(2026-09-07 기준, 총 477건): MATCH 36 / TRANSFER 102 / PLAYER 10 / OTHER 329, NULL 0건. (키워드 보강 전 370건 기준 최초 분포는 MATCH 17 / TRANSFER 55 / PLAYER 9 / OTHER 289였음 — 이후 신규 수집 107건이 자동 분류되며 총량과 비율이 변함)
- 알려진 한계(의도적으로 보류): 하이픈 없는 스코어라인("Newcastle 2 Liverpool 2" 형식), "proposed move"/"approach"처럼 오탐 위험이 큰 표현은 키워드에 추가하지 않음. OTHER 비중은 실제로 상당수가 킷 발매/굿즈/심판 판정 논란/팟캐스트 세그먼트 등 "리그 전반 이슈"라 정당한 분류로 판단됨(표본 검토 완료)
- 테스트: 백엔드 `ArticleControllerTest`/`ArticleRepositoryTest`, collector `test_article_classifier.py`/`test_backfill_categories.py`/`test_rumor_clusterer.py`(스테이지 키워드) — 전부 통과(2026-09-07 재실행)
- **커밋 없음** — git 커밋 로그로는 이 기능의 존재를 알 수 없음

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

- 코드: `translator/translate.py`의 `ENGINE = "argos"`(기본, 오프라인/무료). Claude(Anthropic) 기반 `anthropic_engine.py`는 삭제하지 않고 그대로 보존(`ENGINE` 값만 바꾸면 전환 가능, `ANTHROPIC_API_KEY` 필요)
- **비활성화 이유**: 사용자 확인(2026-09-06) — Argos Translate 번역 품질 문제로 번역 기능 자체를 보류한 상태. 자동으로 다시 도는 스케줄/트리거가 있는지 이번에 재확인했고, 없음을 확인함(아래 12번 참고와 별개로 이 기능 자체가 안 켜져 있음)
- DB: `translations` 테이블 **0건** — 이 환경에서 실제 번역이 단 한 번도 실행된 적 없음을 확인
- 환경 확인: `argostranslate` 패키지가 이 환경엔 원래 설치돼 있지 않았음(2026-09-07 직접 설치 후 테스트 실행). 설치 후에도 **Argos 오프라인 언어 모델 자체는 설치되어 있지 않음**(`argostranslate.package.get_installed_packages()` → 빈 배열) — 즉 `setup_argos_model.py`가 이 환경에서 실행된 적이 없어서, 지금 당장 `translate.py`를 돌려도 실제 번역은 실패함
- 테스트: `translator/tests/` 48개 — `argostranslate` 설치 후 전부 통과(단, 이 테스트들은 mock 기반 단위 테스트이고 실제 모델 다운로드/번역 성공을 검증하지 않음)

### 12. translator 자동 실행 여부 (참고 — 배치 자동화)

**❌ 미구현(연결 안 됨)** — 이건 "기능"이 아니라 "자동화가 없다"는 사실 확인

- `collector/scheduler.py`는 `run_collection_job`(RSS 수집)만 30분 간격으로 스케줄링하며 `translator/` 모듈은 어디서도 import/호출하지 않음
- Windows 작업 스케줄러에 관련 등록 작업 없음, cron/`.bat`/`.ps1`/CI 워크플로우 어디에도 자동 실행 경로 없음
- `translate.py`의 `run_translation_batch()`는 `if __name__ == "__main__":` 안에만 있어 직접 실행하지 않는 한 동작하지 않음
- 확인일: 2026-09-06, 2026-09-07 두 차례 재확인

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

`source_tier`: 1=공식/대형 매체, 2=자체 취재하는 전문 매체, 3=팬 블로그 성격. robots.txt/AI 크롤러 차단 문구를 확인 후 제외한 후보(BBC, Guardian, ESPN, Marca, Football Italia, talkSPORT, Metro, Liverpool Echo)도 `sources.py` 주석에 근거와 함께 기록되어 있음.

---

## 테스트 스위트 전체 결과 (2026-09-07 재실행 기준)

| 모듈 | 결과 | 비고 |
|---|---|---|
| backend (`./gradlew test`) | ✅ 11개 클래스, 53개 테스트, 0 실패 | ⚠️ 이 프로젝트는 `build.gradle`에서 빌드 출력을 `%TEMP%/liverpool-news-backend-build`로 리다이렉트함(OneDrive 동기화 문제 회피) — `backend/build/`(프로젝트 폴더 안)의 결과는 2026-09-01자 stale 데이터이니 절대 참고하지 말 것 |
| collector (`pytest tests/`) | ✅ 124개 테스트, 0 실패 | |
| translator (`pytest tests/`) | ✅ 48개 테스트, 0 실패 | `argostranslate` 패키지가 원래 미설치 상태였음(설치 후 통과) |
| frontend-web (`vitest run`) | ✅ 9개 파일, 39개 테스트, 0 실패 | |

## DB 현재 상태 스냅샷 (2026-09-07, 로컬 MySQL80 `footballnews`)

| 테이블/항목 | 값 |
|---|---|
| articles | 477건 |
| article_clubs | 529행 |
| articles.quoted_reporter 채워짐 | 7건 |
| articles.image_url 채워짐 | 75건 |
| articles.category 분포 | MATCH 36 / TRANSFER 102 / PLAYER 10 / OTHER 329 |
| rumor_threads | 18건 (cross_reported=true 0건) |
| rumor_thread_articles | 21건 |
| users | 1건 |
| user_preferences | 1건 (favorite_club_id 설정 0건) |
| translations | 0건 |
| clubs | 50건 |
