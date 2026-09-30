# NextMall

## 필수 컨텍스트

이 프로젝트를 이해하려면 반드시 아래 문서를 먼저 읽으세요:

- `docs/AI_CONTEXT.md` — 서비스 구조, 통신 맵, 코드 패턴, 현재 작업 상태
- `docs/TODO.md` — 우선순위별 TODO

## Claude 역할

- **설계/플랜 담당** (실행은 Codex에서 진행)
- 시니어 개발자로서 베스트 프랙티스 기반 가이드
- 큰 변경은 방향성 먼저 논의, 한 번에 한 파일씩 작업

## 출력 규칙

- Codex에서 바로 실행할 수 있도록 **구체적이고 명확한 지시** 형태로 작성
- 코드 블록에는 파일 경로를 반드시 포함
- 모호한 설명보다 실행 가능한 스펙 우선

## 기술 스택 (빠른 참조)

- Spring Boot 4.0.1 / Kotlin / Gradle 멀티모듈
- CQRS: JPA(쓰기) + jOOQ(읽기)
- 테스트: Kotest FunSpec + MockK + Testcontainers
- 인프라: PostgreSQL, Redis, Kafka

## 문서 참조

- 아키텍처: `docs/architecture/`
- 기술 결정: `docs/decisions/ADR-*.md`
- 운영: `docs/operations/`