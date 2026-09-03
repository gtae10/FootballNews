# Translator

Anthropic API(Claude)를 사용해 수집된 기사를 한국어로 요약 번역하는 모듈입니다.

## 실행 방법

```bash
pip install -r requirements.txt --break-system-packages
cp .env.example .env  # ANTHROPIC_API_KEY, 필요 시 TRANSLATOR_DB_URL 설정
python translate.py
```

`TRANSLATOR_DB_URL`을 지정하지 않으면 `backend/docker-compose.yml`로 띄운 로컬 MySQL
(`mysql+pymysql://root:password@localhost:3306/liverpool_news`)에 연결을 시도한다.
collector와 동일한 `articles`/`translations` 테이블 스키마를 사용하므로, 먼저 backend를
한 번 실행해 테이블이 생성된 상태여야 한다.

`translator/.env`가 있으면 `db.py` import 시점에 `python-dotenv`가 `ANTHROPIC_API_KEY`,
`TRANSLATOR_DB_URL`을 자동으로 읽어들여 별도 `export` 없이 `python translate.py`만
실행해도 값이 적용된다. `.env`가 없으면 에러 없이 위 기본 접속 정보로 동작하며(단,
`ANTHROPIC_API_KEY`가 없으면 실제 번역 호출 시점에 인증 에러가 발생한다).

`ANTHROPIC_API_KEY`가 아직 없어 실제 번역은 못 하더라도, DB 조회 → 번역 호출 → 저장 →
status 갱신으로 이어지는 파이프라인 배관 자체는 `tests/test_translate_pipeline.py`에서
Anthropic 클라이언트만 mock으로 대체해 이미 검증되어 있다.

## 동작 방식

1. `db.fetch_untranslated_articles()`로 `articles.status = 'COLLECTED'`인 기사를 조회한다.
2. 각 기사를 `translate_article()`로 번역한다. 시스템 프롬프트에 `glossary.py`의 축구
   용어집을 포함해 번역 용어를 일관되게 유지하고, 전문을 그대로 옮기지 않고 핵심 내용
   위주로 3~5문장 요약하도록 지시한다 ([저작권 문서](../docs/LEGAL_NOTES.md) 참고).
3. 번역 결과를 `translations` 테이블에 저장하고, 해당 기사의 `status`를 `TRANSLATED`로
   갱신한다 (`db.save_translation()`).

## 파일 구성

- `translate.py`: 미번역 기사를 조회해 LLM으로 번역하는 메인 로직
- `db.py`: 미번역 기사 조회 및 번역 결과 저장 (backend와 동일한 DB 스키마 사용)
- `glossary.py`: 축구 용어 일관성을 위한 용어집
- `tests/`: 단위/통합 테스트 (LLM 호출은 mock 처리, DB 로직은 in-memory DB로 검증)
