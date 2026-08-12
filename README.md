# Studyme Memory Bot v2

Discord 단체 채팅에서 사람·사건·취향·약속·관계 변화를 출처와 공개 범위와 함께 기억하는 AI 챗봇입니다. Studyme3의 자연스러운 Discord 대화 UX는 계승하고, 기억 저장은 검증기를 반드시 통과하도록 분리했습니다.

## 현재 구현된 MVP

- 멘션, DM, 봇 답장, `WAKE_WORD` 호명어 응답
- 다른 사람 멘션 시 침묵, 웃음 메시지에는 반응, 불확실할 때 침묵
- 채널별 최근 대화와 참여 상태 PostgreSQL 영속화
- 유저·메시지·기억·수정 이력·관계·관계 이벤트·대화 요약 모델
- `guild`, `channel`, `dm_private`, `user_private` 공개 범위
- 서버/채널/DM 범위를 SQL 조회 조건에서 강제
- 별도 LLM 기억 후보 추출기와 민감정보·근거·추론 검증기
- 중복 갱신, 충돌 시 `superseded` 또는 `disputed`, 수정 이력 보존
- OpenAI, Gemini, Grok 호환 제공자와 테스트용 가짜 제공자
- `/기억보기`, `/기억검색`, `/기억수정`, `/기억삭제`, `/나를잊어`, `/기억끄기`, `/기억켜기`, `/서버기억설정`, `/봇정보`
- `/health` PostgreSQL·Redis 상태 확인
- 실제 AI/Discord API를 호출하지 않는 자동 테스트

첫 버전은 텍스트 기억 정확도에 집중합니다. 이미지 장기 기억과 자발적 끼어들기의 LLM 판단은 안전한 기본값으로 꺼져 있습니다.

## 빠른 시작

필요 조건은 Python 3.12, PostgreSQL 16 + pgvector, Redis 7입니다.

```bash
cp .env.example .env
# .env에 Discord 토큰과 선택한 LLM API 키 입력
docker compose up --build
```

Discord Developer Portal에서 봇의 **Message Content Intent**를 켜야 합니다. 초대 권한에는 메시지 보기/보내기, 메시지 기록 보기, 반응 추가와 `applications.commands` scope가 필요합니다.

상태 확인:

```bash
curl http://localhost:8080/health
```

호스트에서 직접 실행:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
alembic upgrade head
python -m app.main
```

## 환경 변수

| 이름 | 설명 | 기본값 |
|---|---|---|
| `DISCORD_TOKEN` | Discord 봇 토큰 | 필수 |
| `DATABASE_URL` | SQLAlchemy 비동기 PostgreSQL URL | 로컬 Compose |
| `REDIS_URL` | Redis URL | `redis://localhost:6379/0` |
| `LLM_PROVIDER` | `openai`, `gemini`, `grok`, `fake` | `openai` |
| `WAKE_WORD` | 봇 호명어 | `스터디미야` |
| `MEMORY_EXTRACTION_ENABLED` | 응답 후 기억 후보 추출 | `true` |
| `AUTO_PARTICIPATION_ENABLED` | 자발적 참여 판단 허용 | `false` |
| `RUN_BOT` | `false`면 상태 서버만 실행 | `true` |

모든 비밀값은 배포 서비스의 환경 변수로 주입합니다. `.env`, 런타임 데이터와 로그는 Git에서 제외됩니다.

## 데이터 경계

```text
Discord 원문 → 정규화/원문 저장 → 참여 판단 → 범위 제한 Context → 답변
                                                      ↓
응답 완료 ←──────────────────────────────────── 기억 후보 추출
                                                      ↓
                                  민감정보/중복/충돌/범위 검증
                                                      ↓
                                   Memory / Revision / Relation Event
```

`dm_private` 기억은 같은 DM 채널에서만 조회됩니다. 서버 기억은 같은 `guild_id`에 한정되고, `channel` 기억은 같은 채널까지 일치해야 합니다. `user_private` 기억은 소유자 관리 명령에는 보이지만 대화 프롬프트에는 주입되지 않습니다.

## 개발 검사

```bash
ruff check .
ruff format --check .
pytest -q
python -m compileall -q app tests
```

## 기존 Studyme3 데이터

기존 전역 ChromaDB 기억에는 서버·DM 출처가 없으므로 자동으로 공개 기억으로 승격하면 안 됩니다. [마이그레이션 계획](docs/migration-plan.md)에 따라 먼저 감사 보고서를 만들고, 출처가 불명확한 기억은 `user_private` 격리 구역으로만 가져옵니다.

## 운영 원칙

- 응답 모델은 DB 쓰기 도구를 받지 않습니다.
- 기억하지 않는 것이 잘못 기억하는 것보다 낫습니다.
- 원문 사실과 추론은 `is_explicit`와 신뢰도로 구분합니다.
- 유저 본인만 자신의 비공개 기억을 조회·수정·삭제합니다.
- 이미지 영구 저장은 기본 비활성화입니다.
- 로그에 토큰, DM 원문, 기억 본문을 남기지 않습니다.

라이선스는 [MIT](LICENSE)입니다.

## Render 스테이징

`render.yaml`은 비용이 발생하지 않는 스테이징용 웹 서비스, PostgreSQL, Key Value를
생성합니다. 무료 웹 서비스는 유휴 시 중지될 수 있으므로 실제 Discord 상시 운영 전에는
봇 서비스를 `worker`/`starter`로 전환해야 합니다. 이 전환은 Render 요금이 발생합니다.
