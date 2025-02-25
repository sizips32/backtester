import sqlite3
from sqlite3 import Error
import os
from datetime import datetime

DATABASE_PATH = "data/portfolio.db"

def ensure_db_directory():
    """데이터베이스 파일을 저장할 디렉토리가 없으면 생성"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

def get_db_connection():
    """데이터베이스 연결을 생성하고 반환"""
    try:
        ensure_db_directory()
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Error as e:
        print(f"데이터베이스 연결 중 오류 발생: {e}")
        return None

def init_db():
    """데이터베이스 초기화 및 테이블 생성"""
    conn = get_db_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # 포트폴리오 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 포트폴리오 투자종목 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio_holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    quantity REAL NOT NULL DEFAULT 0,
                    purchase_price REAL NOT NULL DEFAULT 0,
                    purchase_date DATE,
                    asset_type TEXT DEFAULT 'Stock',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios (id) 
                    ON DELETE CASCADE,
                    UNIQUE (portfolio_id, symbol)
                )
            ''')
            
            # 포트폴리오 성과 이력 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    total_value REAL NOT NULL,
                    daily_return REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios (id) 
                    ON DELETE CASCADE,
                    UNIQUE (portfolio_id, date)
                )
            ''')
            
            conn.commit()
        except Error as e:
            print(f"테이블 생성 중 오류 발생: {e}")
        finally:
            conn.close()

# 포트폴리오 관리 함수들

def create_portfolio(name, description=""):
    """새로운 포트폴리오 생성"""
    conn = get_db_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO portfolios (name, description)
                VALUES (?, ?)
            ''', (name, description))
            conn.commit()
            return cursor.lastrowid
        except Error as e:
            print(f"포트폴리오 생성 중 오류 발생: {e}")
            return None
        finally:
            conn.close()

def get_all_portfolios():
    """모든 포트폴리오 목록 조회"""
    conn = get_db_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM portfolios ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]
        except Error as e:
            print(f"포트폴리오 목록 조회 중 오류 발생: {e}")
            return []
        finally:
            conn.close()

def get_portfolio_by_id(portfolio_id):
    """ID로 포트폴리오 조회"""
    conn = get_db_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM portfolios WHERE id = ?', (portfolio_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Error as e:
            print(f"포트폴리오 조회 중 오류 발생: {e}")
            return None
        finally:
            conn.close()

def update_portfolio(portfolio_id, name, description):
    """포트폴리오 정보 업데이트"""
    conn = get_db_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE portfolios 
                SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (name, description, portfolio_id))
            conn.commit()
            return cursor.rowcount > 0
        except Error as e:
            print(f"포트폴리오 업데이트 중 오류 발생: {e}")
            return False
        finally:
            conn.close()

def delete_portfolio(portfolio_id):
    """포트폴리오 삭제"""
    conn = get_db_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM portfolios WHERE id = ?', (portfolio_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Error as e:
            print(f"포트폴리오 삭제 중 오류 발생: {e}")
            return False
        finally:
            conn.close()

# 포트폴리오 종목 관리 함수들

def add_holding_to_portfolio(portfolio_id, symbol, quantity, purchase_price, purchase_date=None, asset_type="Stock"):
    """포트폴리오에 새로운 종목 추가"""
    conn = get_db_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO portfolio_holdings 
                (portfolio_id, symbol, quantity, purchase_price, purchase_date, asset_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (portfolio_id, symbol, quantity, purchase_price, purchase_date, asset_type))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # 이미 존재하는 경우 업데이트
            cursor.execute('''
                UPDATE portfolio_holdings
                SET quantity = quantity + ?, 
                    purchase_price = (purchase_price * quantity + ? * ?) / (quantity + ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE portfolio_id = ? AND symbol = ?
            ''', (quantity, purchase_price, quantity, quantity, portfolio_id, symbol))
            conn.commit()
            return cursor.lastrowid
        except Error as e:
            print(f"종목 추가 중 오류 발생: {e}")
            return None
        finally:
            conn.close()

def get_portfolio_holdings(portfolio_id):
    """포트폴리오의 모든 보유 종목 조회"""
    conn = get_db_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM portfolio_holdings
                WHERE portfolio_id = ?
                ORDER BY symbol
            ''', (portfolio_id,))
            return [dict(row) for row in cursor.fetchall()]
        except Error as e:
            print(f"포트폴리오 종목 조회 중 오류 발생: {e}")
            return []
        finally:
            conn.close()

def update_holding(holding_id, quantity, purchase_price, purchase_date=None, asset_type=None):
    """포트폴리오 종목 정보 업데이트"""
    conn = get_db_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # asset_type이나 purchase_date가 None이면 기존 값 유지
            if asset_type is None or purchase_date is None:
                existing = cursor.execute(
                    'SELECT asset_type, purchase_date FROM portfolio_holdings WHERE id = ?', 
                    (holding_id,)
                ).fetchone()
                
                if existing:
                    if asset_type is None:
                        asset_type = existing['asset_type']
                    if purchase_date is None:
                        purchase_date = existing['purchase_date']
            
            cursor.execute('''
                UPDATE portfolio_holdings
                SET quantity = ?, 
                    purchase_price = ?,
                    purchase_date = ?,
                    asset_type = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (quantity, purchase_price, purchase_date, asset_type, holding_id))
            conn.commit()
            return cursor.rowcount > 0
        except Error as e:
            print(f"종목 업데이트 중 오류 발생: {e}")
            return False
        finally:
            conn.close()

def delete_holding(holding_id):
    """포트폴리오에서 종목 삭제"""
    conn = get_db_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM portfolio_holdings WHERE id = ?', (holding_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Error as e:
            print(f"종목 삭제 중 오류 발생: {e}")
            return False
        finally:
            conn.close()

# 포트폴리오 성과 관리 함수들

def record_portfolio_performance(portfolio_id, date, total_value, daily_return=None):
    """포트폴리오의 일일 성과 기록"""
    conn = get_db_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO portfolio_performance
                (portfolio_id, date, total_value, daily_return)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(portfolio_id, date) 
                DO UPDATE SET
                    total_value = excluded.total_value,
                    daily_return = excluded.daily_return
            ''', (portfolio_id, date, total_value, daily_return))
            conn.commit()
            return True
        except Error as e:
            print(f"성과 기록 중 오류 발생: {e}")
            return False
        finally:
            conn.close()

def get_portfolio_performance(portfolio_id, start_date=None, end_date=None):
    """포트폴리오의 성과 이력 조회"""
    conn = get_db_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM portfolio_performance WHERE portfolio_id = ?'
            params = [portfolio_id]
            
            if start_date:
                query += ' AND date >= ?'
                params.append(start_date)
            
            if end_date:
                query += ' AND date <= ?'
                params.append(end_date)
                
            query += ' ORDER BY date'
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Error as e:
            print(f"성과 이력 조회 중 오류 발생: {e}")
            return []
        finally:
            conn.close()

# 데이터베이스 초기화
init_db() 
