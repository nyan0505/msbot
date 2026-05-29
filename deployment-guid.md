# msbot Deployment Guide (Server)

이 문서는 `/home/dongyoon/Desktop/msbot` 경로 기준의 실제 배포 절차입니다.

## 1. 사전 확인

- Docker/Compose 사용 가능
- 포트 충돌 없음 확인
- 이 배포는 호스트 포트 `3978` 사용

포트 확인:

```bash
ss -ltnH | grep ':3978 ' || echo '3978 free'
```

## 2. 환경변수 준비

```bash
cd /home/dongyoon/Desktop/msbot
cp .env.example .env
```

`.env`에 아래 값을 채웁니다.

- `MicrosoftAppId`
- `MicrosoftAppPassword`
- `AZURE_TENANT_ID`
- `LITELLM_BASE_URL`
- `BEARER_TOKEN`
- 필요 시 `LITELLM_MODEL`

## 3. 빌드 및 실행

```bash
cd /home/dongyoon/Desktop/msbot
docker compose up -d --build
```

## 4. 배포 검증

컨테이너 상태:

```bash
docker compose ps
docker logs --tail 100 msbot
```

헬스 엔드포인트:

```bash
curl -i http://127.0.0.1:3978/api/messages
```

정상 기준:

- `msbot` 컨테이너가 `Up` 상태
- `/api/messages` 응답 코드 `200`

## 5. 운영 명령

재시작:

```bash
docker compose restart msbot
```

중지:

```bash
docker compose stop msbot
```

갱신 배포(코드 반영):

```bash
git pull
docker compose up -d --build
```

## 6. 트러블슈팅

- 포트 충돌: `docker-compose.yml`의 `3978:3978`에서 왼쪽 포트를 빈 포트로 변경
- 인증 오류: `.env`의 Microsoft Bot 인증 값 재확인
- LLM 연결 오류: `LITELLM_BASE_URL`과 `BEARER_TOKEN` 확인
