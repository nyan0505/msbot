개발 범위 정리
먼저 당신 담당이 아닌 것부터 확실히 선 긋겠습니다.
[당신 담당 X]
- LiteLLM 서버 세팅 및 모델 연결
- LLM 모델 자체
- 사내 GPU 서버 관리

[당신 담당 O]
- MS 365 Agents SDK 봇 서버
- Teams 앱 등록 및 배포
- LiteLLM 서버와의 연동
- M365 데이터 검색 연동 (Teams 채팅 기록, Outlook 이메일)

개발 계획
Phase 1 — 환경 준비 (Day 1~2)
Azure 리소스 세팅
[ ] Azure Portal 접속
[ ] Microsoft Entra ID → 앱 등록
    → App ID 발급
    → App Secret 발급
[ ] Azure Bot Service 리소스 생성
    → 위 App ID 연결
[ ] Bot Service에서 Teams 채널 활성화
[ ] Microsoft Graph API 권한 추가 및 관리자 동의
    → Teams 채팅 조회 권한 (예: Chat.Read 계열)
    → Outlook 메일 조회 권한 (예: Mail.Read 계열)
    → 사용자 위임(Delegated) + OBO 방식 적용 여부 확인
로컬 개발 환경
[ ] Python 3.11 설치
[ ] 프로젝트 폴더 생성
[ ] pip install microsoft-agents-hosting-aiohttp
[ ] .env 파일 작성 (App ID, Secret)
[ ] Bot Framework Emulator 설치 (로컬 테스트용)

Phase 2 — 봇 서버 개발 (Day 3~5)
구현 원칙
[ ] Phase 2 기능은 MS 365 Agents SDK Agent 모듈 기반으로만 구현

MS 365 Agents SDK 사용 기능 (명시)
[ ] Agent 초기화 및 실행 루프 구성
    - Agent 인스트럭션/시스템 프롬프트 구성
    - 메시지 Activity 처리 핸들러 등록
[ ] CloudAdapter + Bot 인증 모듈 연결
    - Bot Service/Teams 요청 토큰 검증
    - on_turn_error 전역 에러 핸들러 등록
[ ] AIOHTTP Hosting 모듈로 /api/messages 라우팅 연결
[ ] TurnContext 기반 응답 처리
    - 일반 텍스트 응답
    - 타이핑 인디케이터 Activity 전송
[ ] Agent Tool 호출 패턴 적용
    - LiteLLM 호출 도구
    - M365 검색 도구 (Teams/Outlook)

기본 뼈대 구현
[ ] /api/messages 엔드포인트 구현
[ ] CloudAdapter 인증 연결
[ ] /agent 커맨드 파싱
[ ] 타이핑 인디케이터 (답변 생성 중 표시)
[ ] 에러 핸들링
    - LiteLLM 서버 다운됐을 때
    - 응답 타임아웃
    - 빈 질문 입력
LiteLLM 연동
[ ] LLM 담당자에게 확인
    - LiteLLM 서버 사내 주소
    - model_name
[ ] call_llm() 함수 구현
[ ] 연동 테스트

M365 검색 연동
[ ] 검색 범위 정의
    - Teams 채팅 기록
    - Outlook 이메일 본문
[ ] Graph 클라이언트 인증 연결 (Delegated/OBO)
[ ] search_teams_messages() 구현
[ ] search_outlook_messages() 구현
[ ] 검색 결과 통합/정렬 (top-k)
[ ] call_llm()에 검색 컨텍스트 주입 (RAG)
[ ] 응답에 출처 표시
    - 메일: 제목/발신자/날짜
    - 채팅: 시간/참여자/대화 요약
[ ] 권한 에러/빈 결과/타임아웃 처리

Phase 3 — 로컬 테스트 (Day 6~7)
[ ] Bot Framework Emulator로 단독 테스트
[ ] ngrok으로 외부 노출
[ ] Azure Bot Service Messaging Endpoint 등록
    예) https://xxxx.ngrok.io/api/messages
[ ] Teams에서 실제 동작 확인
    - /agent 커맨드 자동완성 뜨는지
    - 질문 → 응답 흐름
    - 에러 메시지 노출 확인
[ ] M365 검색 동작 확인
    - Teams 채팅 기록 기반 질의 응답
    - Outlook 이메일 본문 기반 질의 응답
    - 권한 없는 데이터 차단 확인

Phase 4 — 사내 서버 배포 (Day 8~10)
Docker 패키징
[ ] Dockerfile 작성
[ ] docker-compose.yml 작성
[ ] .env 프로덕션용 작성
[ ] 사내 서버에 Docker 배포
IT팀 요청 (미리 해두기)
[ ] 봇 서버용 사내 도메인 or 공인 IP 할당
[ ] 443 포트 인바운드 오픈
[ ] Azure Bot Service Messaging Endpoint를
    ngrok → 사내 도메인으로 교체

Phase 5 — Teams 앱 배포 (Day 11~12)
[ ] manifest.json 작성
    - App ID 입력
    - /agent 커맨드 등록
[ ] 아이콘 이미지 준비 (192x192, 32x32 png)
[ ] zip으로 패키징
    manifest.json + color.png + outline.png
[ ] Teams 관리자에게 사내 앱 배포 요청
    (Teams 관리 센터에서 승인 필요)
[ ] 전체 E2E 테스트