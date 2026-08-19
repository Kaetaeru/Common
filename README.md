# Common — Windows 워크숍 설치 가이드

컴퓨터, Git, GitHub를 처음 사용하는 사람을 기준으로 만든 **영상용 설치 체크리스트**입니다.

목표는 워크숍 시작 전에 필요한 프로그램과 계정을 준비하고, 마지막에 `bun setup-common.ts` 검사를 통과하는 것입니다.

## 영상에서 따라갈 순서

1. [계정과 구독 준비](checklists/01-accounts.md)
2. [Windows 사전 확인](checklists/02-windows-precheck.md)
3. [설치 파일 준비와 자동 설치](checklists/03-install.md)
4. [Git 설정과 GitHub 로그인](checklists/04-git-github.md)
5. [데스크탑 앱과 프로젝트 설정](checklists/05-project.md)
6. [최종 검사와 문제 해결](checklists/06-final-check.md)

## 전체 완료 기준

- [ ] Claude Pro 또는 Max 사용 가능
- [ ] Gemini Advanced 사용 가능
- [ ] GitHub 계정 준비 완료
- [ ] Windows 설치 스크립트 실행 완료
- [ ] Git 사용자 이름과 이메일 설정 완료
- [ ] `gh auth status`에서 GitHub 로그인 확인
- [ ] 필요한 프로젝트 환경 설정 완료
- [ ] `bun setup-common.ts` 결과에서 필요한 항목이 모두 ✅

## 영상 제작 시 가장 중요한 원칙

### 1. 명령어보다 먼저 “어디를 눌러야 하는지” 보여주기
초보자는 `PowerShell`, `터미널`, `관리자 권한`, `현재 폴더` 같은 개념부터 낯설 수 있습니다. 명령어만 화면에 띄우지 말고 **시작 메뉴 검색 → 우클릭 → 관리자 권한으로 실행 → 폴더 이동 → 명령어 입력** 순서를 실제 화면으로 보여주세요.

### 2. Git/GitHub 설정은 설치 후 진행
원본 사전 체크리스트에는 Git 사용자 설정과 `gh auth login`이 포함되어 있지만, 완전히 비어 있는 Windows에서는 Git과 GitHub CLI가 먼저 설치되어야 실행할 수 있습니다. 영상에서는 **자동 설치 → 터미널 재시작 → Git 설정 → GitHub 로그인** 순서로 진행합니다.

### 3. API Key를 미리 만들게 하지 않기
워크숍 기본 실습은 Claude/Gemini 구독 모델을 사용합니다. `.env` 등에 별도 API Key가 필요한 경우에만 운영자 안내에 따라 설정합니다.

### 4. Docker와 WSL2는 기본 설치 항목이 아님
운영자가 별도로 요구하지 않는다면 초보자 영상에서는 건너뜁니다.

### 5. 마지막 장면은 반드시 검증 화면
영상의 종료 기준은 “설치가 끝났다”가 아니라 **`bun setup-common.ts`를 실행해서 필요한 항목이 모두 ✅인지 확인하는 것**입니다.

## 기준 문서

이 레포지토리의 체크리스트는 다음 워크숍 문서를 영상용으로 재구성한 것입니다.

- `SETUP_ko.md`
- `SETUP_CHECKLIST_ko.md`

명령어나 필수 도구가 변경되면 위 원본 문서와 함께 이 체크리스트도 갱신하세요.
