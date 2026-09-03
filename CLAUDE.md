# Liverpool News App

리버풀 FC 뉴스 수집 + 번역 서비스. 백엔드(Spring Boot), 수집기/번역기(Python), 웹(React)로 구성된 멀티 모듈 프로젝트.

## 프로젝트 구조

- `backend/` — Spring Boot REST API (Java 17)
- `collector/` — RSS + 크롤링 기반 뉴스 수집기 (Python)
- `translator/` — LLM 기반 번역 파이프라인 (Python)
- `frontend-web/` — React 웹 클라이언트
- `docs/` — 아키텍처, API, DB 스키마, 저작권 문서

각 폴더 작업은 원칙적으로 해당 폴더 안에서만 하고, 다른 모듈 코드를 임의로 건드리지 않는다.

## 빌드 및 테스트

### backend
- 빌드: `./gradlew build`
- 실행: `./gradlew bootRun`
- 테스트: `./gradlew test`

### collector / translator
- 의존성 설치: `pip install -r requirements.txt --break-system-packages`
- 테스트: `python -m pytest tests/ -v`

### frontend-web
- 설치: `npm install`
- 개발 서버: `npm run dev`
- 테스트: `npm test`

## 코드 스타일

- Java: 4칸 들여쓰기, 클래스명 PascalCase, 메서드/변수 camelCase
- Python: PEP 8 준수, 함수/변수 snake_case
- React: 함수형 컴포넌트만 사용, 컴포넌트 파일명 PascalCase(`App.jsx`)
- 커밋 메시지: 한글로 작성, 이슈 있으면 `#이슈번호` 포함

## 새 기능 작업 시 규칙

- **새 기능을 추가할 때는 항상 테스트 코드를 함께 작성한다.** (백엔드는 JUnit, Python은 pytest)
- API 엔드포인트 추가/변경 시 `docs/API.md`를 함께 업데이트한다.
- DB 스키마 변경 시 `docs/DB_SCHEMA.md`를 함께 업데이트한다.

## 금지 사항

- `backend/src/main/resources/application.yml`에 실제 DB 비밀번호나 API 키를 하드코딩하지 않는다. 환경 변수로 주입한다.
- `.env`, `.env.local` 파일은 읽거나 커밋하지 않는다.
- 뉴스 기사 원문을 전문 그대로 저장/게시하는 로직을 추가하지 않는다. 요약 번역 + 원문 링크 방식만 사용한다. (`docs/LEGAL_NOTES.md` 참고)
- 크롤링 대상 사이트 추가 시 `robots.txt`와 이용약관을 먼저 확인하고 `collector/sources.py`에 추가한다.

## 워크플로우

- 로컬 DB는 `docker-compose up`으로 띄운다 (backend 폴더 기준).
- PR 전 체크리스트: 해당 모듈 테스트 통과 → 관련 문서(`docs/`) 갱신 확인 → 커밋
- 브랜치명: `feature/설명`, `fix/설명` 형식

## 참고 문서

- 아키텍처 개요: `docs/ARCHITECTURE.md`
- API 명세: `docs/API.md`
- DB 스키마: `docs/DB_SCHEMA.md`
- 저작권/법적 고려사항: `docs/LEGAL_NOTES.md`
