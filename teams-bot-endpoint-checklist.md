# Teams/Bot Service Endpoint 최종 점검 체크리스트

대상 서비스: `msbot`

배포 기준 엔드포인트:
- `https://msbot.hdhyundai-erc.com/api/messages`

## 1) 인프라/컨테이너

- [ ] `docker compose ps`에서 `msbot`가 `Up (healthy)` 상태
- [ ] `msbot` 컨테이너가 `hderc-internal-network`에 연결됨
- [ ] Traefik 라우팅 응답 확인 (`401`이어도 라우팅 자체는 정상)

검증 명령:

```bash
cd /home/dongyoon/Desktop/msbot
docker compose ps
docker inspect msbot --format '{{json .NetworkSettings.Networks}}'
curl -k -I --resolve msbot.hdhyundai-erc.com:443:127.0.0.1 https://msbot.hdhyundai-erc.com/api/messages
```

## 2) Azure Bot 설정

- [ ] Azure Bot Service `MicrosoftAppId`가 `.env`의 `MicrosoftAppId`와 동일
- [ ] Azure Bot Service 연결 Secret이 `.env`의 `MicrosoftAppPassword`와 일치
- [ ] 테넌트가 `SingleTenant` 설정과 일치
- [ ] Teams Channel 활성화

## 3) Messaging Endpoint 설정

Azure Bot Service > Configuration > Messaging endpoint:
- [ ] `https://msbot.hdhyundai-erc.com/api/messages` 입력
- [ ] Save 후 검증 성공

참고:
- 엔드포인트의 익명 호출은 앱 미들웨어에서 `401`이 정상
- 실제 Teams/Bot 호출은 `Authorization` 헤더 포함으로 처리됨

## 4) Teams 앱(Manifest) 점검

- [ ] Manifest의 `botId`가 `MicrosoftAppId`와 동일
- [ ] `scopes`가 의도한 범위(`personal`, `team`, `groupchat`)로 설정
- [ ] Command에 `/agent` 포함
- [ ] 앱 재패키징 후 Teams 업로드/업데이트 완료

## 5) 기능 E2E 테스트

- [ ] Teams에서 `/agent` 명령 입력 시 응답 수신
- [ ] 빈 메시지 처리(가이드 문구) 정상
- [ ] LiteLLM 경유 답변 생성 정상
- [ ] M365 검색 권한 부족 시 에러가 크래시 없이 처리됨

## 6) 운영/장애 대응

- [ ] 최근 로그 확인
- [ ] 컨테이너 재시작 테스트
- [ ] 배포 롤백 절차 확인

명령:

```bash
docker logs --tail 200 msbot
docker compose restart msbot
```

## 7) 이번 배포 기준 값 (기록)

- 앱 경로: `/home/dongyoon/Desktop/msbot`
- 공개 엔드포인트: `https://msbot.hdhyundai-erc.com/api/messages`
- 내부 앱 포트: `3978/tcp`
- 외부 직접 포트 노출: 없음 (Traefik 경유)
