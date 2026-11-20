# Studyme Memory Bot v4 - this is no longer supported. only Studyme2, 3 and New 5 is useable

[![CI](https://github.com/mclusky0626/Studyme4/actions/workflows/ci.yml/badge.svg)](https://github.com/mclusky0626/Studyme4/actions/workflows/ci.yml)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Fmclusky0626%2FStudyme4)

Discord 단체 채팅에서 사람·사건·취향·약속·관계 변화를 출처와 공개 범위와 함께 기억하는 AI 챗봇입니다. Studyme3의 자연스러운 Discord 대화 UX는 계승하고, 기억 저장은 검증기를 반드시 통과하도록 분리했습니다.

## 현재 구현된 MVP

- 멘션, DM, 봇 답장, `WAKE_WORD` 호명어 응답
- 접두사 없는 메시지도 최근 흐름을 LLM 또는 Ollama가 판단해 `reply/react/ignore`
- 답변의 의미 단위를 사람처럼 최대 4개의 Discord 말풍선으로 분리
- Markdown 파일로 관리하는 길고 구체적인 페르소나
- 채널별 최근 대화와 참여 상태 PostgreSQL 영속화
- 유저·메시지·기억·수정 이력·관계·관계 이벤트·대화 요약 모델
- `guild`, `channel`, `dm_private`, `user_private` 공개 범위
- 서버/채널/DM 범위를 SQL 조회 조건에서 강제
- 별도 LLM 기억 후보 추출기와 민감정보·근거·추론 검증기
- 중복 갱신, 충돌 시 `superseded` 또는 `disputed`, 수정 이력 보존
- OpenAI, Gemini, Grok 호환 제공자와 테스트용 가짜 제공자
- `/기억보기`, `/기억검색`, `/기억수정`, `/기억삭제`, `/나를잊어`, `/기억끄기`, `/기억켜기`, `/서버기억설정`, `/서버참여설정`, `/봇정보`
- `/health` PostgreSQL·Redis 상태 확인
- 실제 AI/Discord API를 호출하지 않는 자동 테스트

첫 버전은 텍스트 기억 정확도에 집중합니다. 이미지 장기 기억은 비활성화되어 있고,
접두사 없는 참여 판단은 확신이 낮거나 판단 모델이 실패하면 침묵합니다.

## 맥에서 가장 쉽게 실행

Finder에서 **`미유 실행.command`**를 더블클릭하세요.

처음 실행할 때만 다음 작업을 자동으로 처리합니다.

1. Discord 봇 토큰과 LLM API 키를 보이지 않게 입력받음
2. 대화 모델과 접두사 없는 대화 감지 방식 선택
3. 프로젝트 전용 Python 환경과 패키지 자동 설치
4. 로컬 SQLite 데이터베이스 생성과 마이그레이션
5. 미유 실행

두 번째 실행부터는 `미유 실행.command`만 더블클릭하면 바로 시작합니다. 실행 중 열린
Terminal 창을 닫거나 `Ctrl+C`를 누르면 종료됩니다. 설정을 바꾸려면 **`미유 설정.command`**를
실행하세요.

macOS가 처음 실행을 막으면 파일을 우클릭하고 **열기**를 한 번 선택하세요. Python 3.12
이상이 없다는 안내가 나올 때만 다음 명령으로 설치하면 됩니다.

```bash
brew install python@3.12
```

이 로컬 구동 방식에는 Docker, PostgreSQL, Redis가 필요하지 않습니다. 기억은
`data/studyme.db`에 저장되며 `.env`와 함께 Git에 포함되지 않습니다.

## Docker로 실행

여러 PC나 서버에서 PostgreSQL·Redis 구성까지 동일하게 재현해야 할 때만 사용합니다.

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

터미널에서 직접 실행하고 싶다면:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
python scripts/local_launcher.py run
```

## 환경 변수

| 이름 | 설명 | 기본값 |
|---|---|---|
| `DISCORD_TOKEN` | Discord 봇 토큰 | 필수 |
| `DATABASE_URL` | 로컬 SQLite 또는 배포 PostgreSQL URL | 로컬 SQLite |
| `REDIS_URL` | 선택형 Redis URL | 비어 있음 |
| `LLM_PROVIDER` | `openai`, `gemini`, `grok`, `fake` | `openai` |
| `WAKE_WORD` | 봇 호명어 | `스터디미야` |
| `BOT_PERSONA_FILE` | 긴 UTF-8 페르소나 파일 | `persona.md` |
| `BOT_PERSONA` | 파일이 없을 때 사용할 문자열 페르소나 | 기본 말투 |
| `MEMORY_EXTRACTION_ENABLED` | 응답 후 기억 후보 추출 | `true` |
| `AUTO_PARTICIPATION_ENABLED` | 접두사 없는 참여 판단 허용 | `true` |
| `PARTICIPATION_JUDGE_PROVIDER` | `llm`, `ollama`, `off` | `llm` |
| `OLLAMA_PARTICIPATION_MODEL` | 참여 판단 전용 로컬 모델 | `qwen2.5:3b` |
| `RESPONSE_MAX_BUBBLES` | 답변당 최대 말풍선 수 | `4` |
| `RUN_BOT` | `false`면 상태 서버만 실행 | `true` |

모든 비밀값은 배포 서비스의 환경 변수로 주입합니다. `.env`, 런타임 데이터와 로그는 Git에서 제외됩니다.

## 긴 페르소나 편집

기본 [persona.md](persona.md)를 원하는 만큼 길게 편집하면 재시작할 때 적용됩니다. 정체성,
말투, 성격, 관심사, 유저별 태도와 금지 행동을 Markdown 제목으로 나누어 적을 수 있습니다.
파일 대신 환경 변수 한 줄만 쓰려면 `BOT_PERSONA_FILE=`로 비우고 `BOT_PERSONA`를 설정하세요.

## 접두사 없는 대화 감지

기본값 `PARTICIPATION_JUDGE_PROVIDER=llm`은 현재 대화 모델을 작은 추가 판단 호출에도
사용합니다. 로컬 Ollama로 비용을 분리하려면 호스트에서 다음을 실행하세요.

```bash
ollama pull qwen2.5:3b
# .env
PARTICIPATION_JUDGE_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_PARTICIPATION_MODEL=qwen2.5:3b
```

명시적인 DM·멘션·답장·호명은 모델 호출 없이 즉시 답합니다. 다른 유저 멘션은 즉시
무시하고, 그 외 애매한 메시지만 최근 8개 발언과 직전 대화 상대를 보고 판단합니다.
판단 결과가 설정된 신뢰도보다 낮거나 Ollama가 꺼져 있으면 답하지 않습니다. 서버
관리자는 `/서버참여설정`으로 이 기능을 서버별로 끌 수 있습니다.

## 여러 말풍선 답변

응답 모델은 자연스러운 경계에 `[[BUBBLE]]`을 넣고, 전송기가 이를 제거한 뒤 별도 Discord
메시지로 보냅니다. 모델이 경계를 누락해도 긴 답변은 문장과 길이를 기준으로 안전하게
분할합니다. `RESPONSE_MAX_BUBBLES`와 `RESPONSE_BUBBLE_MAX_CHARS`로 조절할 수 있습니다.

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
