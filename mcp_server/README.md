# Portfolio BackTester MCP Server

Claude Desktop용 포트폴리오 백테스터 MCP 서버입니다.

## 🚀 주요 기능

### 1. 📊 포트폴리오 구성
- **create_portfolio**: 새 포트폴리오 생성
- **optimize_portfolio**: 최적 자산 비중 계산 (최소분산, 리스크패리티, 마코위츠)
- **rebalance_portfolio**: 리밸런싱 계획 수립

### 2. 📏 포지션 사이징
- **calculate_position_size**: 최적 포지션 크기 계산
  - Kelly Criterion
  - Risk-based sizing
  - Fixed percentage
  - Fixed amount

### 3. 📈 백테스팅
- **backtest_portfolio**: 과거 성과 시뮬레이션
- **compare_strategies**: 여러 전략 비교 분석

### 4. 🛡️ 리스크 분석
- **analyze_risk**: VaR, CVaR, 변동성 등 리스크 지표 계산

### 5. 📊 시장 데이터
- **get_market_data**: 실시간 및 과거 시장 데이터 조회

## 🛠️ 설치 방법

### 1. 의존성 설치
```bash
cd mcp_server
pip install -r requirements.txt
```

### 2. Claude Desktop 설정

#### 방법 1: 수동 설정
1. Claude Desktop 열기
2. 설정 → Developer 탭
3. "Edit Config" 클릭
4. `claude_desktop_config.json` 내용 추가:

```json
{
  "mcpServers": {
    "portfolio-backtester": {
      "command": "python",
      "args": [
        "/path/to/portfolio_mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/path/to/BackTester"
      }
    }
  }
}
```

#### 방법 2: 자동 설정
제공된 `claude_desktop_config.json` 파일을 Claude Desktop 설정에 복사

### 3. Claude Desktop 재시작

## 💬 사용 예시

### 포트폴리오 생성
```
"애플, 구글, 마이크로소프트로 균등 비중 포트폴리오 만들어줘"
```

### 포트폴리오 최적화
```
"AAPL, GOOGL, MSFT, AMZN으로 최소 분산 포트폴리오 구성해줘"
```

### 포지션 사이징
```
"테슬라 주가 250달러, 계좌 10만 달러일 때 Kelly Criterion으로 포지션 크기 계산해줘"
```

### 백테스팅
```
"내 포트폴리오로 2023년 1월부터 백테스팅 실행해줘"
```

### 리스크 분석
```
"현재 포트폴리오의 VaR와 리스크 지표 분석해줘"
```

### 리밸런싱
```
"포트폴리오가 목표 비중에서 5% 이상 벗어났는지 확인해줘"
```

## 🏗️ 아키텍처

### 도구 구조
```
MCP Server
├── Portfolio Management
│   ├── create_portfolio
│   ├── optimize_portfolio
│   └── rebalance_portfolio
├── Position Sizing
│   └── calculate_position_size
├── Analysis
│   ├── backtest_portfolio
│   ├── analyze_risk
│   └── compare_strategies
└── Data
    └── get_market_data
```

### 최적화 알고리즘
- **Minimum Variance**: 변동성 최소화
- **Risk Parity**: 리스크 균등 배분
- **Markowitz**: 샤프 비율 최대화

### 포지션 사이징 방법
- **Kelly Criterion**: 기대 수익 최대화
- **Risk-Based**: 손실 제한
- **Fixed Percentage**: 계좌 대비 고정 비율
- **Fixed Amount**: 고정 금액

## 📋 개발 로드맵

### Phase 1 (완료) ✅
- 기본 MCP 서버 구조
- 핵심 도구 구현
- Claude Desktop 통합

### Phase 2 (예정)
- 데이터베이스 연동
- 실시간 데이터 피드
- 고급 최적화 알고리즘

### Phase 3 (예정)
- 웹 인터페이스 연동
- 알림 시스템
- 자동 거래 연동

## 🤝 기여하기

이슈와 PR은 언제든 환영합니다!

## 📄 라이선스

MIT License