import pandas as pd
import pdfplumber
import re
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.models import Transaction, Portfolio, TransactionType

class ImportService:
    def __init__(self, db: Session):
        self.db = db
    
    def import_trading212_pdf(self, file_content, portfolio_id: int):
        """Import transactions from Trading212 Monthly Statement PDF"""
        try:
            imported = 0
            skipped = 0
            errors = []
            
            with pdfplumber.open(file_content) as pdf:
                current_date = None
                
                for page in pdf.pages:
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    lines = text.split('\n')
                    for line in lines:
                        try:
                            # Pattern 1: Tarih satırını yakala (YYYY-MM-DD formatında tek başına)
                            date_match = re.match(r'^(\d{4}-\d{2}-\d{2})$', line.strip())
                            if date_match:
                                current_date = date_match.group(1)
                                continue
                            
                            # Pattern 2: Tarih + Symbol aynı satırda (eski format)
                            # 2025-11-03 11:00:03 IREN AU0000185993 USD ... Buy/Sell
                            full_match = re.match(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+([A-Z0-9]{1,6})\s+\w+\s+\w+\s+\d+\s+\d+\s+(Buy|Sell)\s+([\d.]+)\s+([\d.]+)', line)
                            if full_match:
                                date_str, symbol, direction, qty_str, price_str = full_match.groups()
                                tx_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                                quantity = float(qty_str)
                                price = float(price_str)
                                
                                # Check duplicate
                                existing = self.db.query(Transaction).filter(
                                    Transaction.portfolio_id == portfolio_id,
                                    Transaction.symbol == symbol,
                                    Transaction.quantity == quantity,
                                    Transaction.price == price,
                                    Transaction.date == tx_date
                                ).first()
                                
                                if existing:
                                    skipped += 1
                                    continue
                                
                                tx_type = TransactionType.BUY if direction == 'Buy' else TransactionType.SELL
                                
                                transaction = Transaction(
                                    portfolio_id=portfolio_id,
                                    symbol=symbol,
                                    transaction_type=tx_type,
                                    quantity=quantity,
                                    price=price,
                                    fee=0,
                                    date=tx_date
                                )
                                self.db.add(transaction)
                                imported += 1
                                continue
                            
                            # Pattern 3: Tarih inline ile başlıyor (YYYY-MM-DD SYMBOL ...)
                            date_inline = re.match(r'^(\d{4}-\d{2}-\d{2})\s+([A-Z0-9]{1,6})', line)
                            if date_inline:
                                current_date = date_inline.group(1)
                            
                            # Pattern 4: Symbol ile başlayan satır (yeni format - tarih ayrı satırda)
                            # SOFI US83406F1021 USD 25951185699 25951185777 Buy 4 15.19 ...
                            if 'Buy' in line or 'Sell' in line:
                                match = re.match(r'^([A-Z0-9]{1,6})\s+.*?(Buy|Sell)\s+([\d.]+)\s+([\d.]+)', line)
                                if match and current_date:
                                    symbol, direction, qty_str, price_str = match.groups()
                                    
                                    # Saat bilgisi varsa al, yoksa 00:00:00 kullan
                                    time_match = re.search(r'(\d{2}:\d{2}:\d{2})', line)
                                    if time_match:
                                        tx_date = datetime.strptime(f"{current_date} {time_match.group(1)}", '%Y-%m-%d %H:%M:%S')
                                    else:
                                        tx_date = datetime.strptime(current_date, '%Y-%m-%d')
                                    
                                    quantity = float(qty_str)
                                    price = float(price_str)
                                    
                                    # Check duplicate
                                    existing = self.db.query(Transaction).filter(
                                        Transaction.portfolio_id == portfolio_id,
                                        Transaction.symbol == symbol,
                                        Transaction.quantity == quantity,
                                        Transaction.price == price,
                                        Transaction.date == tx_date
                                    ).first()
                                    
                                    if existing:
                                        skipped += 1
                                        continue
                                    
                                    tx_type = TransactionType.BUY if direction == 'Buy' else TransactionType.SELL
                                    
                                    transaction = Transaction(
                                        portfolio_id=portfolio_id,
                                        symbol=symbol,
                                        transaction_type=tx_type,
                                        quantity=quantity,
                                        price=price,
                                        fee=0,
                                        date=tx_date
                                    )
                                    self.db.add(transaction)
                                    imported += 1
                        
                        except Exception as e:
                            errors.append(f"Line parse error: {str(e)}")
            
            self.db.commit()
            
            return {
                "success": True,
                "imported": imported,
                "skipped": skipped,
                "errors": errors[:20]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "imported": 0,
                "skipped": 0
            }
    
    def import_trading212_csv(self, file_content, portfolio_id: int):
        """Import transactions from Trading212 CSV export"""
        try:
            df = pd.read_csv(file_content)
            
            imported = 0
            skipped = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    action = str(row.get('Action', '')).lower()
                    
                    if 'buy' in action:
                        tx_type = TransactionType.BUY
                    elif 'sell' in action:
                        tx_type = TransactionType.SELL
                    else:
                        skipped += 1
                        continue
                    
                    symbol = str(row.get('Ticker', '')).strip()
                    if not symbol:
                        skipped += 1
                        continue
                    
                    quantity = float(row.get('No. of shares', 0))
                    price = float(row.get('Price / share', 0))
                    
                    time_str = row.get('Time', '')
                    try:
                        tx_date = datetime.strptime(str(time_str), '%Y-%m-%d %H:%M:%S')
                    except:
                        try:
                            tx_date = datetime.strptime(str(time_str), '%d/%m/%Y %H:%M:%S')
                        except:
                            tx_date = datetime.utcnow()
                    
                    existing = self.db.query(Transaction).filter(
                        Transaction.portfolio_id == portfolio_id,
                        Transaction.symbol == symbol,
                        Transaction.date == tx_date,
                        Transaction.quantity == quantity
                    ).first()
                    
                    if existing:
                        skipped += 1
                        continue
                    
                    transaction = Transaction(
                        portfolio_id=portfolio_id,
                        symbol=symbol,
                        transaction_type=tx_type,
                        quantity=quantity,
                        price=price,
                        fee=0,
                        date=tx_date
                    )
                    
                    self.db.add(transaction)
                    imported += 1
                    
                except Exception as e:
                    errors.append(f"Row {index}: {str(e)}")
            
            self.db.commit()
            
            return {
                "success": True,
                "imported": imported,
                "skipped": skipped,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "imported": 0,
                "skipped": 0
            }
    
    def import_generic_csv(self, file_content, portfolio_id: int, column_mapping: dict):
        """Import transactions from generic CSV with custom column mapping"""
        try:
            df = pd.read_csv(file_content)
            
            imported = 0
            skipped = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    action = str(row.get(column_mapping.get('action', 'Action'), '')).lower()
                    
                    if 'buy' in action or 'kauf' in action:
                        tx_type = TransactionType.BUY
                    elif 'sell' in action or 'verkauf' in action:
                        tx_type = TransactionType.SELL
                    else:
                        skipped += 1
                        continue
                    
                    symbol = str(row.get(column_mapping.get('symbol', 'Symbol'), '')).strip()
                    if not symbol:
                        skipped += 1
                        continue
                    
                    quantity = float(row.get(column_mapping.get('quantity', 'Quantity'), 0))
                    price = float(row.get(column_mapping.get('price', 'Price'), 0))
                    fee = float(row.get(column_mapping.get('fee', 'Fee'), 0) or 0)
                    
                    date_str = row.get(column_mapping.get('date', 'Date'), '')
                    date_format = column_mapping.get('date_format', '%Y-%m-%d')
                    
                    try:
                        tx_date = datetime.strptime(str(date_str), date_format)
                    except:
                        tx_date = datetime.utcnow()
                    
                    transaction = Transaction(
                        portfolio_id=portfolio_id,
                        symbol=symbol,
                        transaction_type=tx_type,
                        quantity=quantity,
                        price=price,
                        fee=fee,
                        date=tx_date
                    )
                    
                    self.db.add(transaction)
                    imported += 1
                    
                except Exception as e:
                    errors.append(f"Row {index}: {str(e)}")
            
            self.db.commit()
            
            return {
                "success": True,
                "imported": imported,
                "skipped": skipped,
                "errors": errors
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "imported": 0,
                "skipped": 0
            }