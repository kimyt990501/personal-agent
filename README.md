# Personal Agent

Ollama 로컬 LLM 기반 Discord 개인 AI 비서.

Mac Mini M4에서 Ollama를 통해 LLM을 로컬 실행하고, Discord DM으로 대화하는 개인 비서 봇입니다.
명령어 없이 자연어로 날씨, 환율, 리마인더, 페르소나 변경 등을 처리하는 Tool Calling 시스템을 포함합니다.

## 주요 기능

### 자연어 Tool Calling

명령어 없이 자연어로 대화하면 LLM이 필요한 도구를 자동으로 호출합니다.

- **날씨** - "오늘 서울 날씨 어때?" -> Open-Meteo API로 현재 날씨, 최저/최고 기온, 강수확률 등 조회
- **환율** - "100달러 원화로 얼마야?" -> 실시간 환율 조회 후 변환
- **리마인더** - "30분 후에 회의 알려줘" -> 리마인더 자동 등록, 시간 되면 DM 발송
- **페르소나** - "이름을 뽀삐로 바꿔줘" -> AI 비서의 이름, 역할, 말투를 자연어로 변경

### 명령어 기반 기능

| 명령어 | 설명 |
|--------|------|
| `/cmd` | 전체 명령어 도움말 |
| `/ping` | Ollama 연결 상태 확인 |
| `/clear` | 대화 기록 초기화 |
| `/persona` | 현재 페르소나 확인 |
| `/newme` | 페르소나 + 대화 기록 전체 초기화 |
| `/s <검색어>` | DuckDuckGo 웹 검색 후 AI 요약 |
| `/m <내용>` | 메모 저장 / `/m list` 목록 / `/m del <번호>` 삭제 / `/m find <검색어>` 검색 |
| `/r <시간> <내용>` | 리마인더 설정 / `/r list` 목록 / `/r del <번호>` 삭제 |
| `/w <도시>` | 날씨 조회 |
| `/ex <금액> <FROM> <TO>` | 환율 변환 (예: `/ex 100 USD KRW`) |
| `/t <언어> <내용>` | 번역 (예: `/t en 안녕하세요`) |
| `/pick <항목들>` | 랜덤 선택 (예: `/pick 짜장 짬뽕 볶음밥`) |
| `/fs <경로>` | 파일시스템 조회 |

### 기타

- **URL 요약** - 메시지에 URL 포함 시 자동으로 본문 추출 후 AI가 요약
- **파일 분석** - Discord에 파일 첨부 시 내용 추출 (텍스트, PDF 지원)
- **대화 맥락 유지** - SQLite에 대화 이력 저장, 이전 대화를 기억하며 응답
- **페르소나** - 첫 대화 시 이름/역할/말투 3단계 설정, 이후 자연어로 변경 가능

## 기술 스택

| 구분 | 기술 |
|------|------|
| LLM | Ollama + qwen2.5-coder:14b |
| 봇 | discord.py |
| DB | SQLite (aiosqlite) |
| 날씨 | Open-Meteo API (무료, API 키 불필요) |
| 환율 | ExchangeRate API (무료) |
| 웹 검색 | DuckDuckGo (ddgs) |
| 웹 추출 | trafilatura |
| HTTP | aiohttp |

## 설치 및 실행

### 사전 요구사항

- Python 3.11+
- [Ollama](https://ollama.com) 설치 및 모델 다운로드
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications)에서 발급)

### 설치

```bash
git clone <repo-url>
cd personal-agent

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Ollama 모델 준비

```bash
# 기본 모델 다운로드
ollama pull qwen2.5-coder:14b

# (선택) 커스텀 모델 생성 - 컨텍스트 윈도우 확장
ollama create my-model -f Modelfile
```

### 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 `DISCORD_TOKEN`을 설정합니다. 커스텀 모델을 사용하는 경우 `OLLAMA_MODEL`도 변경합니다.

```
DISCORD_TOKEN=your_discord_bot_token
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:14b
MAX_HISTORY_LENGTH=20
```

### 실행

```bash
# 직접 실행
python -m src.main

# 또는 run.sh 스크립트 사용
./run.sh start     # 백그라운드 실행
./run.sh stop      # 중지
./run.sh restart   # 재시작
./run.sh log       # 로그 확인
./run.sh status    # 상태 확인
```

## 프로젝트 구조

```
src/
├── bot/
│   ├── client.py           # 메인 봇 클라이언트, 메시지 라우팅
│   └── handlers/           # 기능별 핸들러
│       ├── chat.py         # 일반 대화 + Tool Calling 엔진
│       ├── commands.py     # 기본 명령어
│       ├── memo.py         # 메모
│       ├── reminder.py     # 리마인더
│       ├── search.py       # 웹 검색
│       ├── persona.py      # 페르소나 초기 설정
│       ├── weather.py      # 날씨 (명령어)
│       ├── exchange.py     # 환율 (명령어)
│       ├── translate.py    # 번역
│       ├── pick.py         # 랜덤 선택
│       ├── filesystem.py   # 파일시스템
│       └── file.py         # 파일 첨부 처리
├── db/                     # SQLite 데이터베이스 레이어
├── llm/
│   └── ollama_client.py    # Ollama 클라이언트, 시스템 프롬프트 관리
├── utils/
│   ├── web.py              # URL 추출, 웹 콘텐츠 가져오기
│   ├── time_parser.py      # 한국어 시간 표현 파싱
│   └── weather.py          # Open-Meteo API 클라이언트
├── config.py               # 환경 변수 로드
└── main.py                 # 진입점
```

## Tool Calling 동작 방식

이 봇은 LLM의 응답에서 특정 태그 패턴을 감지하여 외부 API를 호출하는 방식으로 Tool Calling을 구현합니다.

```
사용자: "오늘 서울 날씨 알려줘"
  -> LLM 응답: [WEATHER:서울]
  -> Open-Meteo API 호출
  -> 결과를 LLM에 재전달
  -> LLM: "서울은 현재 맑고 기온은 3.2도입니다. 체감온도는 -1도이고..."
```

시스템 프롬프트에 도구 사용 규칙을 정의하고, LLM이 도구가 필요하다고 판단하면 약속된 태그 형식으로 응답합니다. `chat.py`의 `_chat_with_tools()` 메서드가 이 태그를 정규식으로 감지하고, 해당 API/DB를 호출한 뒤 결과를 다시 LLM에 전달하여 자연어 응답을 생성합니다.
