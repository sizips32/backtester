# 포트폴리오 백테스터 (Portfolio BackTester)

## 프로젝트 개요

포트폴리오 백테스터는 한국 및 미국 시장을 지원하는 종합적인 금융 분석 시스템입니다. Streamlit 기반의 직관적인 웹 인터페이스를 통해 포트폴리오 백테스팅, 리스크 분석, 자산 배분 최적화, 포지션 사이징 등의 기능을 제공합니다.

## 🌟 주요 기능

### 📊 포트폴리오 관리
- **저장된 포트폴리오 지원**: SQLite 데이터베이스를 통한 포트폴리오 영구 저장
- **탭 분리 인터페이스**: 저장된 포트폴리오와 수동 입력 방식 선택 가능
- **실시간 포트폴리오 추적**: 현재 가격 기반 실시간 성과 모니터링
- **포트폴리오 비교**: 여러 포트폴리오 성과 동시 비교

### 🔍 분석 기능

#### 백테스팅 엔진
- **기간별 성과 분석**: 다양한 기간 설정으로 성과 측정
- **거래 비용 반영**: 실제 거래 환경을 고려한 시뮬레이션
- **누적 수익률 추적**: 시각적 성과 그래프 제공
- **벤치마크 비교**: 주요 지수 대비 상대 성과 분석

#### 리스크 분석 (저장된 포트폴리오 + 수동 입력 지원)
- **종합 리스크 지표**: Sharpe Ratio, Sortino Ratio, Calmar Ratio
- **VaR/CVaR 분석**: 다양한 신뢰 구간별 위험 측정
- **최대 낙폭(MDD)**: 포트폴리오 최대 손실 구간 분석
- **변동성 분석**: 연간 변동성 및 위험 조정 수익률
- **벤치마크 지수 성과**: 6개 주요 글로벌 지수와 비교

#### 자산 배분 최적화 (저장된 포트폴리오 + 수동 입력 지원)
- **마코위츠 최적화**: 현대 포트폴리오 이론 기반 최적화
- **최소분산 포트폴리오**: 안정성 중심 최적화
- **리스크 패리티**: 위험 기여도 균등 배분
- **등가중 포트폴리오**: 단순 균등 배분 전략
- **최적화 결과 저장**: 계산된 최적 비중을 포트폴리오에 직접 저장

#### 포트폴리오 리밸런싱 (저장된 포트폴리오 + 수동 입력 지원)
- **임계값 기반 리밸런싱**: 설정 가능한 편차 임계값
- **실시간 현재가 반영**: 최신 시장 가격 기반 계산
- **리밸런싱 제안**: 매수/매도/유지 권장사항 제공
- **비용 효율성**: 거래 비용을 고려한 리밸런싱 계획

#### 포지션 사이징
- **다양한 사이징 전략**: 등가중, 변동성 기반, 리스크 패리티
- **자금 관리**: 투자 가능 자금 기반 포지션 계산
- **리스크 조정**: 개별 종목 리스크 수준 반영

### 🌐 글로벌 시장 지원
- **한국 시장**: KOSPI, KOSDAQ 주식 (종목코드 6자리)
- **미국 시장**: NYSE, NASDAQ 주식 (티커 심볼)
- **글로벌 지수**: S&P500, KOSPI, 나스닥, 다우존스, 일본 니케이, 중국 상해종합

### 💾 데이터 관리
- **통합 데이터 서비스**: yfinance 기반 실시간 데이터 수집
- **자동 fallback**: 데이터 소스 실패 시 자동 대체
- **스마트 캐싱**: TTL 기반 캐시로 성능 최적화
- **데이터 검증**: 수집된 데이터 품질 자동 검증

## 🏗️ 시스템 아키텍처

### 레이어 구조
```
┌─────────────────────────────────────────┐
│           Presentation Layer            │
│     (Streamlit UI Components)          │
├─────────────────────────────────────────┤
│            Business Logic Layer         │
│  (Analysis Modules + Tab Interface)    │
├─────────────────────────────────────────┤
│             Service Layer               │
│        (Data Service + Caching)        │
├─────────────────────────────────────────┤
│            Data Access Layer           │
│     (Repository Pattern + ORM)         │
├─────────────────────────────────────────┤
│              Database Layer             │
│         (SQLite + Portfolio DB)        │
└─────────────────────────────────────────┘
```

### 핵심 디자인 패턴
- **Repository Pattern**: 데이터 접근 추상화
- **Service Layer Pattern**: 비즈니스 로직 분리
- **Dependency Injection**: 설정 및 서비스 주입
- **Error Recovery Pattern**: 포괄적 오류 처리

## 📁 프로젝트 구조

```
BackTester/
├── app.py                          # 메인 Streamlit 애플리케이션
├── config/
│   └── app_config.py              # Pydantic 기반 통합 설정
├── services/
│   └── data_service.py            # 통합 데이터 서비스 (yfinance)
├── repository/                     # Repository Pattern 구현
│   ├── portfolio_repo.py          # 포트폴리오 CRUD
│   ├── holdings_repo.py           # 보유 종목 관리
│   └── target_weights_repo.py     # 목표 비중 관리
├── utils/
│   ├── database.py                # SQLAlchemy ORM 모델
│   ├── error_handler.py           # 포괄적 오류 처리
│   ├── logger.py                  # 구조화된 로깅
│   └── performance_monitor.py     # 성능 모니터링
├── components/
│   ├── portfolio_view.py          # 포트폴리오 뷰 컴포넌트
│   ├── ui_components.py           # 재사용 가능한 UI 컴포넌트
│   └── enhanced_charts.py         # 고급 차트 컴포넌트
├── tests/                         # 테스트 스위트
│   ├── test_data_validation.py    # 데이터 검증 테스트
│   ├── test_integration.py        # 통합 테스트
│   └── test_performance.py        # 성능 테스트
├── data/
│   └── portfolio.db               # SQLite 포트폴리오 데이터베이스
├── 분석 모듈/
│   ├── backtesting.py             # 백테스팅 엔진
│   ├── risk_analysis.py           # 리스크 분석 (탭 분리)
│   ├── asset_allocation.py        # 자산 배분 최적화 (탭 분리)
│   ├── portfolio_rebalancing.py   # 포트폴리오 리밸런싱 (탭 분리)
│   └── position_sizing.py         # 포지션 사이징
├── 최적화 모듈/
│   └── optimization.py            # 포트폴리오 최적화 알고리즘
├── 실행 스크립트/
│   ├── run.py                     # Python 실행 스크립트
│   └── run.sh                     # Shell 실행 스크립트
├── 설정 파일/
│   ├── requirements.txt           # Python 의존성
│   ├── pytest.ini               # 테스트 설정
│   └── .streamlit/config.toml    # Streamlit 설정
└── 문서/
    ├── CLAUDE.md                 # Claude Code 가이드
    ├── SETUP_GUIDE.md            # 설치 가이드
    └── README.md                 # 프로젝트 문서
```

## 🛠️ 기술 스택

### 핵심 프레임워크
- **Python 3.9+**: 메인 프로그래밍 언어
- **Streamlit**: 웹 애플리케이션 프레임워크
- **SQLAlchemy**: ORM 및 데이터베이스 관리
- **Pydantic**: 데이터 검증 및 설정 관리

### 데이터 처리 & 분석
- **NumPy**: 수치 계산
- **Pandas**: 데이터 프레임 조작
- **SciPy**: 통계 및 최적화
- **yfinance**: 금융 데이터 수집

### 시각화
- **Plotly**: 인터랙티브 차트
- **Streamlit Charts**: 기본 차트 컴포넌트

### 데이터베이스 & 저장소
- **SQLite**: 경량 관계형 데이터베이스
- **WAL Mode**: 동시성 향상

### 개발 도구
- **pytest**: 테스트 프레임워크
- **Black**: 코드 포매팅
- **Ruff**: 린팅

## 🚀 설치 및 실행

### 1. 환경 설정

```bash
# 저장소 클론
git clone [repository-url]
cd BackTester

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 애플리케이션 실행

```bash
# 표준 실행 (포트 8501)
streamlit run app.py

# 커스텀 포트 실행 (포트 7700)
streamlit run app.py --server.port=7700

# 제공된 스크립트 사용
python run.py  # Python 스크립트 방식
./run.sh       # Shell 스크립트 방식 (chmod +x run.sh 필요)
```

### 3. 접속
웹 브라우저에서 `http://localhost:7700` (또는 8501) 접속

## 💡 사용 가이드

### 포트폴리오 생성 및 관리
1. **포트폴리오 관리** 페이지에서 새 포트폴리오 생성
2. **종목 추가**: 한국 주식(6자리 숫자) 또는 미국 주식(티커) 입력
3. **목표 비중 설정**: 각 종목별 목표 비중 설정
4. **포트폴리오 저장**: 데이터베이스에 영구 저장

### 분석 수행
1. **탭 선택**: 저장된 포트폴리오 또는 수동 입력 선택
2. **포트폴리오 선택**: (저장된 포트폴리오 탭의 경우) 분석할 포트폴리오 선택
3. **분석 설정**: 기간, 방법론 등 분석 파라미터 설정
4. **실행 및 결과 확인**: 분석 실행 후 시각화된 결과 확인

### 최적화 및 리밸런싱
1. **자산 배분 최적화**: 다양한 최적화 방법론 선택 및 실행
2. **결과 저장**: 최적화된 비중을 포트폴리오에 바로 저장
3. **리밸런싱**: 현재 비중과 목표 비중 차이 기반 리밸런싱 제안

## 🧪 테스트

```bash
# 전체 테스트 실행
pytest

# 커버리지 포함 테스트
pytest --cov=. tests/

# 특정 테스트 모듈 실행
pytest tests/test_data_validation.py
```

## 📊 주요 지표 및 메트릭

### 성과 지표
- **총 수익률**: 기간 전체 수익률
- **연간 수익률**: 연환산 수익률
- **Sharpe Ratio**: 위험 조정 수익률
- **Sortino Ratio**: 하방 위험 조정 수익률
- **Calmar Ratio**: MDD 조정 수익률

### 리스크 지표
- **변동성**: 연간 변동성
- **최대 낙폭(MDD)**: 최대 손실 구간
- **VaR**: 95%, 99% 신뢰구간 Value at Risk
- **CVaR**: 조건부 Value at Risk

### 벤치마크 지수
- **S&P 500** (^GSPC): 미국 대형주 대표 지수
- **KOSPI** (^KS11): 한국 대표 주가지수
- **나스닥** (^IXIC): 미국 기술주 중심 지수
- **다우존스** (^DJI): 미국 산업평균 지수
- **니케이 225** (^N225): 일본 대표 주가지수
- **상해종합** (000001.SS): 중국 대표 주가지수

## 🔧 설정 및 커스터마이징

### 환경 설정
- `config/app_config.py`: 애플리케이션 전체 설정
- API 설정: 타임아웃, 재시도, 캐시 TTL
- 데이터베이스 설정: 연결 풀, WAL 모드
- UI 설정: 테마, 레이아웃 옵션

### 성능 최적화
- **캐시 TTL**: 데이터 캐시 만료 시간 조정
- **병렬 처리**: 멀티스레딩 워커 수 설정
- **메모리 관리**: 대용량 포트폴리오 처리 최적화

## 🤝 기여 방법

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### 개발 가이드라인
- **코드 스타일**: Black 포매터 사용
- **테스트**: 새 기능에 대한 테스트 코드 작성
- **문서화**: 주요 함수 및 클래스에 docstring 추가
- **타입 힌트**: Python 타입 힌트 적극 활용

## 📝 변경 로그

### v2.0 (Latest)
- ✨ 탭 분리 인터페이스 도입 (저장된 포트폴리오 + 수동 입력)
- 🗄️ SQLite 데이터베이스 연동으로 포트폴리오 영구 저장
- 🌍 벤치마크 지수 데이터 문제 해결 (6개 글로벌 지수 지원)
- 🔄 포트폴리오 리밸런싱 기능 개선
- 📊 리스크 분석 고도화 (VaR, CVaR, 다양한 리스크 지표)
- 🎯 자산 배분 최적화 결과 저장 기능
- 🏗️ Repository 패턴 도입으로 아키텍처 개선

### v1.0
- 📈 기본 백테스팅 기능
- 💹 포트폴리오 성과 분석
- 📊 기본 시각화
- 🔍 yfinance 기반 데이터 수집

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 문의사항

프로젝트에 대한 문의사항이나 버그 리포트는 GitHub Issues를 통해 제출해 주세요.

---

**포트폴리오 백테스터**로 스마트한 투자 의사결정을 시작해보세요! 🚀