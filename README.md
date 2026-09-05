# Liverpool News (가제)

해외축구 뉴스를 모아 한국어로 번역해 보여주는 웹 앱입니다. 리버풀 팬 매체는 항상 포함하고,
그 외 대형/전문 매체는 기사 본문에서 언급된 구단을 자동 감지해 태깅합니다. 출처 신뢰도
등급과 유명 기자 인용 감지로 루머와 사실을 구분하고, 같은 이적 건을 타임라인으로 묶어
여러 매체가 교차 보도했는지도 보여줍니다.

## 프로젝트 구조

```
FootballNews/
├── backend/         # Spring Boot REST API 서버
├── collector/       # Python 기반 뉴스 수집기 (RSS)
├── translator/      # LLM(Claude) 기반 번역 파이프라인
├── frontend-web/    # React 웹 클라이언트
└── docs/            # 아키텍처, API, DB 스키마, 저작권 문서
```

## 구현된 기능

- **뉴스 수집** (`collector/`): 7개 RSS 소스(리버풀 팬 매체 3곳 + Sky Sports·Independent·
  Football365·90min)에서 주기적으로 수집. 구단 자동 태깅(5대 리그 50개 구단), 유명
  기자/계정 인용 감지(신뢰도 등급 자동 상향), RSS의 `media:thumbnail`/`enclosure` 등에서
  대표 이미지 URL 추출(이미지 파일은 재호스팅하지 않고 URL만 저장)까지 포함.
- **이적 루머 타임라인**: 같은 (선수, 구단) 건으로 기사를 자동 클러스터링하고, 48시간 이내
  서로 다른 매체가 몇 곳이나 독립 보도했는지 계산해 교차보도 배지를 표시. 규칙 기반이며
  LLM을 쓰지 않는다(정확도 트레이드오프는 `collector/player_extractor.py` 상단 주석 참고).
- **번역 파이프라인** (`translator/`): Claude API로 기사를 요약 번역하는 배관은 구현·검증
  완료. 실제 사용하려면 `translator/.env`에 유효한 `ANTHROPIC_API_KEY`를 설정해야 한다
  (현재 플레이스홀더 상태라 번역은 아직 실행된 적이 없다).
- **API 서버** (`backend/`): 기사 목록/검색/상세, 구단 목록, 루머 스레드, Google OAuth
  로그인, 온보딩/관심 구단/알림 설정, 기자 제보 API 제공. 상세 스펙은 [API.md](docs/API.md).
- **웹 클라이언트** (`frontend-web/`): 피드/검색/기사 상세/설정/온보딩 화면. Google OAuth
  설정이 안 되어 있어도 로그인 화면의 "게스트로 둘러보기"로 피드·검색·상세·루머 타임라인을
  바로 확인할 수 있다(개발 편의용 — 실서비스 전 유지 여부 검토 필요, `frontend-web/README.md`
  참고). 설정, 관심 구단 저장, 기자 제보는 게스트 모드에서 막혀 있다.

## 로컬에서 실행하기

각 모듈의 세부 사항은 하위 폴더 README를 참고한다. 전체를 처음부터 띄우는 순서는 다음과 같다.

1. **MySQL 준비**: `backend/docker-compose.yml`로 띄우거나, 로컬에 직접 설치한 MySQL을
   사용해도 된다. `backend/.env.example`을 복사해 `backend/.env`를 만들고 접속 정보를 맞춘다.
2. **backend 실행** — `articles`/`clubs`/`rumor_threads` 등 테이블을 Hibernate가
   자동 생성한다(`ddl-auto: update`). collector/translator보다 먼저 한 번 띄워야 한다.
   ```bash
   cd backend && ./gradlew bootRun
   ```
   Google 로그인을 실제로 쓰려면 `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`을 Google Cloud
   Console에서 발급받아 `.env`에 넣는다 — 없어도 프론트엔드 게스트 모드로 대부분 기능을
   확인할 수 있다.
3. **collector 실행** — 실제 뉴스 사이트로 네트워크 요청이 나간다.
   ```bash
   cd collector && pip install -r requirements.txt --break-system-packages
   python scheduler.py       # 평소 주기 수집 (최신 기사만)
   python backfill.py        # 과거 기사 백필 (선택, 신규 소스 추가 시 등)
   python build_rumor_threads.py  # 루머 스레드 소급 클러스터링 (선택)
   ```
4. **translator 실행** (선택) — `ANTHROPIC_API_KEY` 필요.
   ```bash
   cd translator && pip install -r requirements.txt --break-system-packages
   python translate.py
   ```
5. **frontend-web 실행**
   ```bash
   cd frontend-web && npm install && npm run dev
   ```
   `http://localhost:5173/login`에서 Google 로그인 또는 게스트 모드로 시작한다.

## 문서

- [아키텍처 개요](docs/ARCHITECTURE.md)
- [API 명세](docs/API.md)
- [DB 스키마](docs/DB_SCHEMA.md)
- [저작권/법적 고려사항](docs/LEGAL_NOTES.md)

## 다음 단계

- 실제 Google OAuth 자격증명 발급 및 연동 확인
- `ANTHROPIC_API_KEY` 연동 후 번역 파이프라인 실사용 확인
- 실서비스 전 게스트 모드 노출 여부 검토
- 모바일 클라이언트 착수
