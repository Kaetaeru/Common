# 04. Git 설정과 GitHub 로그인

이 단계는 **자동 설치가 끝난 뒤** 진행합니다.

## 체크리스트

- [ ] 새 PowerShell 또는 Windows Terminal을 열었다
- [ ] Git 사용자 이름을 설정했다
- [ ] Git 이메일을 설정했다
- [ ] `gh auth login`을 완료했다
- [ ] `gh auth status`에서 로그인 상태를 확인했다

## 1. Git 사용자 이름 설정

```powershell
git config --global user.name "홍길동"
```

자신의 이름으로 바꿔 입력합니다.

## 2. Git 이메일 설정

```powershell
git config --global user.email "you@example.com"
```

가능하면 GitHub에서 사용하는 이메일 주소를 입력합니다.

## 3. 설정 확인

```powershell
git config --global user.name
git config --global user.email
```

입력한 이름과 이메일이 출력되면 완료입니다.

## 4. GitHub 로그인

```powershell
gh auth login
```

터미널의 안내에 따라 진행하고, 브라우저가 열리면 자신의 GitHub 계정으로 인증합니다.

## 5. 로그인 상태 확인

```powershell
gh auth status
```

`Logged in` 상태가 확인되면 완료입니다.

## 영상에서 꼭 설명할 것

### Git과 GitHub는 같은 것이 아님
- Git: PC에서 파일 버전을 관리하는 프로그램
- GitHub: Git 저장소를 온라인에서 보관하고 협업하는 서비스
- `gh`: 터미널에서 GitHub를 다루는 프로그램

처음 배우는 사람에게 이 세 가지를 한 번에 같은 것으로 설명하지 않는 것이 중요합니다.

### 브라우저 인증 화면까지 보여주기
`gh auth login` 명령어만 보여주고 끝내지 말고, 브라우저 인증 후 다시 터미널로 돌아와 `gh auth status`까지 확인합니다.

### 성공 기준은 `gh auth status`
브라우저에서 로그인한 것처럼 보여도 터미널 인증이 끝나지 않았을 수 있습니다. 반드시 마지막 상태 확인까지 보여주세요.
