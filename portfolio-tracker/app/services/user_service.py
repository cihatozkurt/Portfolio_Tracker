import bcrypt
from sqlalchemy.orm import Session
from app.database.models import User, Portfolio

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def register(self, username: str, email: str, password: str):
        """Register a new user"""
        # Check if user exists
        existing = self.db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing:
            return None, "Username or email already exists"
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=password_hash
        )
        self.db.add(user)
        self.db.commit()
        
        # Create default portfolio
        portfolio = Portfolio(name="My Portfolio", user_id=user.id)
        self.db.add(portfolio)
        self.db.commit()
        
        return user, "Registration successful"
    
    def login(self, username: str, password: str):
        """Authenticate user"""
        user = self.db.query(User).filter(User.username == username).first()
        
        if not user:
            return None, "User not found"
        
        if bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            return user, "Login successful"
        
        return None, "Invalid password"
    
    def get_user_portfolio(self, user_id: int):
        """Get user's portfolio"""
        return self.db.query(Portfolio).filter(Portfolio.user_id == user_id).first()