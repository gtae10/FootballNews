# Liverpool News Backend

Spring Boot 3.3 (Java 17) 기반 REST API 서버입니다.

## 요구 사항

- JDK 17
- Docker / Docker Compose (로컬 MySQL 실행용)
- 별도의 Gradle 설치 불필요 — 포함된 Gradle Wrapper(`gradlew`)를 사용합니다.

## 로컬 실행 방법

### 1. MySQL 컨테이너 기동

```bash
docker-compose up -d
```

`liverpool_news` 데이터베이스를 담은 MySQL 8 컨테이너가 `localhost:3306`에 뜹니다.
데이터는 named volume(`mysql_data`)에 저장되어 컨테이너를 재시작해도 유지됩니다.

접속 정보를 바꾸고 싶다면 `.env.example`을 `.env`로 복사한 뒤 값을 수정하세요.

```bash
cp .env.example .env
```

`backend/.env`가 있으면 `./gradlew bootRun` 실행 시 별도로 `export` 하지 않아도 자동으로 읽어들입니다
(`application.yml`의 `spring.config.import: optional:file:.env[.properties]`). `.env`가 없으면 에러 없이
아래 표의 기본값(docker-compose 기본 설정)으로 동작합니다.

### 2. 애플리케이션 빌드 및 실행

```bash
./gradlew build
./gradlew bootRun
```

(Windows PowerShell/CMD에서는 `gradlew.bat build`, `gradlew.bat bootRun`)

기본적으로 `application.yml`은 아래 환경 변수를 읽으며, 값이 없으면 docker-compose 기본값을 사용합니다.

| 환경 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `DB_URL` | `jdbc:mysql://localhost:3306/liverpool_news` | JDBC 접속 URL |
| `DB_USERNAME` | `root` | DB 사용자명 |
| `DB_PASSWORD` | `password` | DB 비밀번호 |

서버는 기본적으로 `8080` 포트에서 기동됩니다.

### 3. 정상 기동 확인

```bash
curl http://localhost:8080/api/v1/articles
```

기사 목록이 없더라도 `200 OK`와 함께 빈 페이지(`{"content":[],...}`) 응답이 오면 정상입니다.

### 4. 종료

```bash
# 애플리케이션은 Ctrl+C로 종료
docker-compose down       # 컨테이너만 중지 (데이터는 유지)
docker-compose down -v    # 컨테이너 + 데이터까지 완전 삭제
```
