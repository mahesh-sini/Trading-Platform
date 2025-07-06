import asyncio
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from services.database import get_db, Base
from services.auth_service import create_access_token
from models.user import User
from models.subscription import Subscription
from models.broker_account import BrokerAccount

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "poolclass": StaticPool,
    },
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "User"
    }

@pytest.fixture
def test_user(db_session, test_user_data):
    """Create a test user in the database"""
    from services.auth_service import get_password_hash
    
    user = User(
        email=test_user_data["email"],
        password_hash=get_password_hash(test_user_data["password"]),
        first_name=test_user_data["first_name"],
        last_name=test_user_data["last_name"],
        subscription_tier="free",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_token(test_user):
    """Create an authentication token for the test user"""
    return create_access_token(data={"sub": str(test_user.id)})

@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers for API requests"""
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.fixture
def test_subscription(db_session, test_user):
    """Create a test subscription"""
    subscription = Subscription(
        user_id=test_user.id,
        tier="basic",
        status="active"
    )
    db_session.add(subscription)
    db_session.commit()
    db_session.refresh(subscription)
    return subscription

@pytest.fixture
def test_broker_account(db_session, test_user):
    """Create a test broker account"""
    broker_account = BrokerAccount(
        user_id=test_user.id,
        broker_name="alpaca",
        account_id="test_account_123",
        api_key="test_api_key",
        api_secret="test_api_secret",
        is_paper=True,
        is_active=True
    )
    db_session.add(broker_account)
    db_session.commit()
    db_session.refresh(broker_account)
    return broker_account

@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return {
        "symbol": "AAPL",
        "price": 150.25,
        "bid": 150.20,
        "ask": 150.30,
        "volume": 1000000,
        "change": 2.50,
        "change_percent": 1.69,
        "market_status": "open"
    }

@pytest.fixture
def sample_order_data():
    """Sample order data for testing"""
    return {
        "symbol": "AAPL",
        "side": "buy",
        "type": "market",
        "quantity": 100
    }

@pytest.fixture
def sample_prediction_data():
    """Sample prediction data for testing"""
    return {
        "symbol": "AAPL",
        "prediction_type": "price",
        "predicted_price": 155.50,
        "confidence": 0.85,
        "horizon": "1d",
        "features_used": ["sma_20", "rsi", "volume"]
    }

# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Mock external services
@pytest.fixture
def mock_broker_api(mocker):
    """Mock broker API responses"""
    mock_api = mocker.patch('services.broker_service.AlpacaBroker')
    mock_instance = mock_api.return_value
    
    # Mock successful order placement
    mock_instance.place_order.return_value = {
        "order_id": "test_order_123",
        "status": "placed",
        "symbol": "AAPL",
        "side": "buy",
        "quantity": 100,
        "type": "market"
    }
    
    # Mock account info
    mock_instance.get_account_info.return_value = {
        "account_id": "test_account_123",
        "cash": 10000.0,
        "portfolio_value": 25000.0,
        "buying_power": 50000.0
    }
    
    return mock_instance

@pytest.fixture
def mock_market_data_api(mocker):
    """Mock market data API responses"""
    mock_api = mocker.patch('services.data_service.DataService')
    mock_instance = mock_api.return_value
    
    # Mock quote data
    mock_instance.get_quote.return_value = {
        "symbol": "AAPL",
        "price": 150.25,
        "bid": 150.20,
        "ask": 150.30,
        "volume": 1000000,
        "change": 2.50,
        "change_percent": 1.69
    }
    
    # Mock historical data
    mock_instance.get_historical_data.return_value = [
        {"date": "2024-01-01", "open": 148.0, "high": 152.0, "low": 147.0, "close": 150.25, "volume": 1000000}
    ]
    
    return mock_instance

@pytest.fixture
def mock_ml_service(mocker):
    """Mock ML service responses"""
    mock_service = mocker.patch('services.ml_service.MLService')
    mock_instance = mock_service.return_value
    
    # Mock prediction
    mock_instance.generate_prediction.return_value = {
        "symbol": "AAPL",
        "predicted_price": 155.50,
        "confidence": 0.85,
        "prediction_type": "price",
        "horizon": "1d"
    }
    
    return mock_instance