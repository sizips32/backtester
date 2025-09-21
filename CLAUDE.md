# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Portfolio BackTester is a comprehensive financial analysis system built with Streamlit that provides portfolio backtesting, risk analysis, asset allocation optimization, and position sizing functionality for Korean and US markets.

## Development Commands

### Running the Application
```bash
# Standard Streamlit execution (port 8501)
streamlit run app.py

# Custom port execution (port 7700)
streamlit run app.py --server.port=7700

# Using provided scripts
python run.py  # Python script method
./run.sh       # Shell script method (requires chmod +x)
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. tests/

# Run specific test file
pytest tests/test_repository.py
```

### Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Architecture Overview

### Core System Design

The application follows a **layered architecture** pattern with clear separation of concerns:

1. **Presentation Layer** (`app.py`, `components/`)
   - Streamlit-based web interface with modular page components
   - Theme management system with dark/light mode support
   - Enhanced UI components for metrics, loading states, and alerts

2. **Business Logic Layer** (feature modules)
   - `backtesting.py`: Historical performance analysis engine with vectorized calculations
   - `risk_analysis.py`: Risk metrics calculation (VaR, Sharpe, Sortino, etc.)
   - `asset_allocation.py`: Portfolio optimization strategies
   - `portfolio_rebalancing.py`: Dynamic rebalancing algorithms
   - `position_sizing.py`: Position size optimization

3. **Service Layer** (`services/`)
   - `data_service.py`: Unified data fetching with automatic fallback between FinanceDataReader and yfinance
   - Implements caching, retry logic, and parallel data fetching
   - Thread-safe operations with configurable workers

4. **Data Access Layer** (`repository/`, `utils/database.py`)
   - SQLAlchemy ORM for portfolio persistence
   - Repository pattern for CRUD operations
   - SQLite with WAL mode for concurrent access

5. **Configuration System** (`config/app_config.py`)
   - Pydantic-based configuration management
   - Environment-aware settings with validation
   - Centralized configuration for API, trading, analysis, database, UI, and logging

### Key Design Patterns

- **Repository Pattern**: Database operations abstracted through repository classes
- **Service Layer Pattern**: Business logic isolated from data access
- **Dependency Injection**: Configuration and services injected where needed
- **Error Recovery Pattern**: Comprehensive error handling with fallback strategies
- **Caching Strategy**: Multi-level caching (Streamlit, LRU, custom cache)

### Data Flow

1. User interacts with Streamlit UI components
2. Business logic modules process requests
3. Data service fetches market data with automatic source fallback
4. Results cached at multiple levels for performance
5. Processed data displayed through enhanced UI components

### Error Handling Architecture

The system implements a sophisticated error recovery system (`utils/error_handler.py`):
- Custom exception hierarchy for different failure scenarios
- Automatic retry with exponential backoff
- Graceful degradation when data sources fail
- User-friendly error messages with recovery suggestions

### Performance Optimizations

- **Vectorized Calculations**: NumPy/Pandas operations for portfolio calculations
- **Parallel Data Fetching**: ThreadPoolExecutor for concurrent API calls
- **Smart Caching**: TTL-based caching with cache key generation
- **Database Optimization**: WAL mode, connection pooling, pragma settings
- **Lazy Loading**: Data fetched only when needed

## Key Technical Considerations

### Data Sources
- Primary: FinanceDataReader for Korean stocks
- Fallback: yfinance for US stocks and when FDR fails
- Automatic ticker format detection and cleaning
- Support for various ticker formats (US stocks, Korean stocks with .KS/.KQ, indices with ^)

### Database Schema
- SQLite database with SQLAlchemy ORM
- Tables: Portfolio, TargetWeights, Holdings, Performance
- Relationships managed through foreign keys
- Automatic migration support via Alembic

### Configuration Management
- Pydantic models for type-safe configuration
- Settings cascade: environment variables → config file → defaults
- Validation at startup to catch configuration errors early

### Logging System
- Structured logging with rotation and retention policies
- Separate logs for application and errors
- Performance metrics tracking through decorators

### Testing Strategy
- Unit tests for repository and analyzer components
- Fixtures for database sessions and sample data
- Mock objects for external API calls

## Common Development Tasks

### Adding a New Portfolio Analysis Feature
1. Create module in root directory following existing pattern
2. Implement `show_[feature_name]()` function for Streamlit interface
3. Add to MENU_OPTIONS in `app.py`
4. Update imports in `app.py`

### Modifying Data Fetching Logic
- Primary logic in `services/data_service.py`
- Implement fallback in `fetch_single_stock()` method
- Update cache key generation if parameters change

### Database Schema Changes
1. Modify models in `utils/database.py`
2. Create Alembic migration: `alembic revision --autogenerate -m "description"`
3. Apply migration: `alembic upgrade head`

### Adding New Configuration
1. Add Pydantic model in `config/app_config.py`
2. Update AppSettings to include new config
3. Access via `get_[config_name]_config()` helper function