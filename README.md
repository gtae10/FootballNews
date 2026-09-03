# Liverpool News (가제)

리버풀 FC 관련 기사만 모아서 한국어로 번역해 보여주는 웹/모바일 앱입니다.

## 개요

여러 해외 매체(공식 사이트, BBC Sport, Sky Sports 등)에서 리버풀 관련 기사를 RSS와
크롤링으로 수집하고, LLM을 이용해 한국어로 번역한 뒤 웹/모바일 클라이언트에서
볼 수 있게 제공하는 서비스입니다.

## 프로젝트 구조

```
liverpool-news-app/
├── backend/         # Spring Boot REST API 서버
├── collector/        # Python 기반 뉴스 수집기 (RSS + 크롤링)
├── translator/        # LLM 기반 번역 파이프라인
├── frontend-web/      # React 웹 클라이언트
└── docs/            # 아키텍처, API, DB 스키마 문서
```

## 문서

- [아키텍처 개요](docs/ARCHITECTURE.md)
- [API 명세](docs/API.md)
- [DB 스키마](docs/DB_SCHEMA.md)
- [저작권/법적 고려사항](docs/LEGAL_NOTES.md)

## 빠른 시작

각 하위 프로젝트(`backend`, `collector`, `translator`, `frontend-web`)의 README를
참고해 개별적으로 실행할 수 있습니다. 현재는 기본 골격(scaffold)만 구성되어 있으며,
실제 수집/번역 로직과 API 구현은 추가 작업이 필요합니다.

## 로드맵 (제안)

1. `collector`: RSS 소스 1~2개로 원문 수집 + DB 저장까지 동작 확인
2. `backend`: 저장된 원문을 조회하는 API 완성
3. `translator`: LLM 번역 파이프라인 연결, 번역 결과 저장
4. `frontend-web`: 기사 목록/상세 화면 구현
5. 모바일 클라이언트 착수
