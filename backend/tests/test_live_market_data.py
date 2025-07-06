import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from datetime import datetime, timedelta

from services.live_market_data import LiveMarketDataService, live_market_data_service


@pytest.mark.unit
@pytest.mark.asyncio
class TestLiveMarketDataService:
    """Test cases for Live Market Data Service"""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance for testing"""
        return LiveMarketDataService()

    @pytest.fixture
    def mock_aiohttp_session(self):
        """Mock aiohttp session"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        return mock_session, mock_response

    async def test_service_initialization(self, service):
        """Test service initializes correctly"""
        assert service.session is None
        assert service.websocket_connections == {}
        assert service.subscribed_symbols == set()
        assert len(service.providers) == 4  # NSE, Yahoo, Alpha Vantage, Polygon
        assert service.providers['nse']['enabled'] is True
        assert service.providers['yahoo_finance']['enabled'] is True

    async def test_service_initialize_and_close(self, service):
        """Test service initialization and cleanup"""
        await service.initialize()
        assert service.session is not None
        assert len(service.rate_limits) == 4

        await service.close()
        # Session should be closed

    @patch('aiohttp.ClientSession')
    async def test_get_live_quote_success(self, mock_session_class, service):
        """Test successful live quote retrieval"""
        # Setup mock response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            'priceInfo': {
                'lastPrice': 2500.75,
                'change': 25.50,
                'pChange': 1.03,
                'open': 2480.25,
                'close': 2475.25,
                'intraDayHighLow': {'max': 2510.00, 'min': 2470.00}
            },
            'info': {'symbol': 'RELIANCE'},
            'securityWiseDP': {'quantityTraded': 1500000}
        }
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value = mock_session
        service.session = mock_session

        # Test the method
        quote = await service.get_live_quote('RELIANCE', 'NSE')

        assert quote is not None
        assert quote['symbol'] == 'RELIANCE'
        assert quote['price'] == 2500.75
        assert quote['change'] == 25.50
        assert quote['change_percent'] == 1.03
        assert quote['exchange'] == 'NSE'
        assert quote['currency'] == 'INR'

    @patch('aiohttp.ClientSession')
    async def test_get_live_quote_nse_fallback_to_yahoo(self, mock_session_class, service):
        """Test fallback from NSE to Yahoo Finance"""
        mock_session = AsyncMock()
        mock_response_nse = AsyncMock()
        mock_response_nse.status = 404  # NSE fails
        
        mock_response_yahoo = AsyncMock()
        mock_response_yahoo.status = 200
        mock_response_yahoo.json.return_value = {
            'chart': {
                'result': [{
                    'meta': {
                        'regularMarketPrice': 2500.75,
                        'previousClose': 2475.25,
                        'regularMarketVolume': 1500000,
                        'regularMarketDayHigh': 2510.00,
                        'regularMarketDayLow': 2470.00,
                        'regularMarketOpen': 2480.25,
                        'currency': 'INR'
                    }
                }]
            }
        }
        
        # Setup mock to return different responses based on URL
        def mock_get(url, params=None):
            mock_resp = AsyncMock()
            if 'nseindia.com' in str(url):
                mock_resp.__aenter__.return_value = mock_response_nse
            else:  # Yahoo Finance
                mock_resp.__aenter__.return_value = mock_response_yahoo
            return mock_resp

        mock_session.get.side_effect = mock_get
        mock_session_class.return_value = mock_session
        service.session = mock_session

        quote = await service.get_live_quote('RELIANCE', 'NSE')

        assert quote is not None
        assert quote['symbol'] == 'RELIANCE'
        assert quote['price'] == 2500.75
        assert quote['exchange'] == 'NSE'  # Should still show NSE even though data from Yahoo

    async def test_normalize_nse_quote(self, service):
        """Test NSE quote normalization"""
        nse_data = {
            'priceInfo': {
                'lastPrice': 2500.75,
                'change': 25.50,
                'pChange': 1.03,
                'open': 2480.25,
                'close': 2475.25,
                'intraDayHighLow': {'max': 2510.00, 'min': 2470.00}
            },
            'info': {'symbol': 'RELIANCE'},
            'securityWiseDP': {'quantityTraded': 1500000}
        }

        normalized = service._normalize_nse_quote(nse_data)

        assert normalized['symbol'] == 'RELIANCE'
        assert normalized['price'] == 2500.75
        assert normalized['change'] == 25.50
        assert normalized['change_percent'] == 1.03
        assert normalized['volume'] == 1500000
        assert normalized['high'] == 2510.00
        assert normalized['low'] == 2470.00
        assert normalized['open'] == 2480.25
        assert normalized['previous_close'] == 2475.25
        assert normalized['exchange'] == 'NSE'
        assert normalized['currency'] == 'INR'
        assert 'timestamp' in normalized

    async def test_normalize_yahoo_quote(self, service):
        """Test Yahoo Finance quote normalization"""
        yahoo_data = {
            'chart': {
                'result': [{
                    'meta': {
                        'regularMarketPrice': 2500.75,
                        'previousClose': 2475.25,
                        'regularMarketVolume': 1500000,
                        'regularMarketDayHigh': 2510.00,
                        'regularMarketDayLow': 2470.00,
                        'regularMarketOpen': 2480.25,
                        'currency': 'INR',
                        'bid': 2500.50,
                        'ask': 2501.00
                    }
                }]
            }
        }

        normalized = service._normalize_yahoo_quote(yahoo_data, 'RELIANCE.NS')

        assert normalized['symbol'] == 'RELIANCE'
        assert normalized['price'] == 2500.75
        assert normalized['change'] == 25.50  # Calculated: 2500.75 - 2475.25
        assert normalized['volume'] == 1500000
        assert normalized['exchange'] == 'NSE'
        assert normalized['currency'] == 'INR'

    async def test_rate_limiting(self, service):
        """Test rate limiting functionality"""
        # Set very low rate limit for testing
        service.providers['nse']['rate_limit'] = 1
        service.rate_limits['nse'] = {'requests': [], 'last_reset': datetime.now()}

        # First request should pass
        assert await service._check_rate_limit('nse') is True
        
        # Second request should fail (rate limited)
        assert await service._check_rate_limit('nse') is False

    @patch('aiohttp.ClientSession')
    async def test_get_historical_data(self, mock_session_class, service):
        """Test historical data retrieval"""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            'chart': {
                'result': [{
                    'timestamp': [1640995200, 1641081600],  # Unix timestamps
                    'indicators': {
                        'quote': [{
                            'open': [2480.25, 2500.00],
                            'high': [2510.00, 2520.00],
                            'low': [2470.00, 2490.00],
                            'close': [2500.75, 2515.50],
                            'volume': [1500000, 1600000]
                        }]
                    }
                }]
            }
        }
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value = mock_session
        service.session = mock_session

        start_date = datetime.now() - timedelta(days=2)
        end_date = datetime.now()
        
        historical_data = await service.get_historical_data(
            'RELIANCE', '1d', start_date, end_date
        )

        assert len(historical_data) == 2
        assert historical_data[0]['open'] == 2480.25
        assert historical_data[0]['close'] == 2500.75
        assert historical_data[1]['close'] == 2515.50

    async def test_subscribe_to_real_time(self, service):
        """Test real-time subscription"""
        symbols = ['RELIANCE', 'TCS', 'INFY']
        
        with patch.object(service, '_real_time_update_loop') as mock_loop:
            await service.subscribe_to_real_time(symbols)
            
            assert len(service.subscribed_symbols) == 3
            assert 'RELIANCE' in service.subscribed_symbols
            assert 'TCS' in service.subscribed_symbols
            assert 'INFY' in service.subscribed_symbols

    async def test_real_time_update_loop_with_mock_connection_manager(self, service):
        """Test real-time update loop"""
        # Mock the connection manager
        service.connection_manager = AsyncMock()
        service.subscribed_symbols.add('RELIANCE')
        
        # Mock get_live_quote to return data once then remove symbol
        call_count = 0
        async def mock_get_quote(symbol, exchange=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {'symbol': symbol, 'price': 2500.75, 'change': 25.50}
            else:
                service.subscribed_symbols.discard(symbol)  # Stop the loop
                return None

        service.get_live_quote = mock_get_quote

        # Start the update loop (it should run once and then stop)
        await service._real_time_update_loop('RELIANCE')
        
        # Verify the connection manager was called
        service.connection_manager.broadcast_to_symbol.assert_called()

    async def test_error_handling_invalid_response(self, service):
        """Test error handling for invalid API responses"""
        service.session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 500
        service.session.get.return_value.__aenter__.return_value = mock_response

        quote = await service.get_live_quote('INVALID', 'NSE')
        assert quote is None

    async def test_normalize_quote_with_missing_data(self, service):
        """Test quote normalization with missing data"""
        incomplete_data = {
            'priceInfo': {
                'lastPrice': 2500.75
                # Missing other fields
            },
            'info': {'symbol': 'RELIANCE'}
        }

        normalized = service._normalize_nse_quote(incomplete_data)
        
        assert normalized['symbol'] == 'RELIANCE'
        assert normalized['price'] == 2500.75
        assert normalized['change'] == 0  # Default value
        assert normalized['volume'] == 0  # Default value


@pytest.mark.integration
@pytest.mark.asyncio
class TestLiveMarketDataAPI:
    """Integration tests for Live Market Data API endpoints"""

    async def test_get_live_quote_endpoint(self, client, auth_headers):
        """Test the live quote API endpoint"""
        with patch.object(live_market_data_service, 'get_live_quote') as mock_get_quote:
            mock_get_quote.return_value = {
                'symbol': 'RELIANCE',
                'price': 2500.75,
                'change': 25.50,
                'change_percent': 1.03,
                'volume': 1500000,
                'exchange': 'NSE',
                'currency': 'INR',
                'timestamp': datetime.now().isoformat()
            }

            response = client.get("/v1/market/quote/RELIANCE", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data['success'] is True
            assert data['data']['symbol'] == 'RELIANCE'
            assert data['data']['price'] == 2500.75

    async def test_get_batch_quotes_endpoint(self, client, auth_headers):
        """Test the batch quotes API endpoint"""
        with patch.object(live_market_data_service, 'get_live_quote') as mock_get_quote:
            mock_get_quote.side_effect = [
                {'symbol': 'RELIANCE', 'price': 2500.75},
                {'symbol': 'TCS', 'price': 3500.25},
                None  # INFY returns None (no data)
            ]

            response = client.get(
                "/v1/market/quotes/batch?symbols=RELIANCE&symbols=TCS&symbols=INFY",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data['success'] is True
            assert len(data['data']['quotes']) == 2
            assert 'RELIANCE' in data['data']['quotes']
            assert 'TCS' in data['data']['quotes']
            assert 'INFY' not in data['data']['quotes']
            assert len(data['data']['errors']) == 1

    async def test_get_indian_indices_endpoint(self, client, auth_headers):
        """Test the Indian indices API endpoint"""
        with patch.object(live_market_data_service, 'get_live_quote') as mock_get_quote:
            mock_get_quote.side_effect = [
                {'price': 19674.25, 'change': 156.80, 'change_percent': 0.80, 'volume': 1000000},
                {'price': 65930.77, 'change': 442.65, 'change_percent': 0.68, 'volume': 2000000},
                None  # BANKNIFTY fails, should use fallback
            ]

            response = client.get("/v1/market/indices", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data['success'] is True
            assert len(data['data']) == 3
            
            # Check NIFTY data
            nifty = next(idx for idx in data['data'] if idx['symbol'] == 'NIFTY')
            assert nifty['price'] == 19674.25
            assert nifty['data_source'] == 'live'
            
            # Check BANKNIFTY fallback
            banknifty = next(idx for idx in data['data'] if idx['symbol'] == 'BANKNIFTY')
            assert banknifty['data_source'] == 'fallback'

    async def test_get_historical_data_endpoint(self, client, auth_headers):
        """Test the historical data API endpoint"""
        mock_historical_data = [
            {
                'timestamp': '2024-01-01T00:00:00+00:00',
                'open': 2480.25,
                'high': 2510.00,
                'low': 2470.00,
                'close': 2500.75,
                'volume': 1500000
            }
        ]
        
        with patch.object(live_market_data_service, 'get_historical_data') as mock_get_hist:
            mock_get_hist.return_value = mock_historical_data

            response = client.get(
                "/v1/market/historical/RELIANCE?period=1d&interval=1d",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data['success'] is True
            assert data['data']['symbol'] == 'RELIANCE'
            assert data['data']['total_bars'] == 1
            assert len(data['data']['bars']) == 1

    async def test_subscribe_to_real_time_endpoint(self, client, auth_headers):
        """Test the real-time subscription API endpoint"""
        with patch.object(live_market_data_service, 'subscribe_to_real_time') as mock_subscribe:
            mock_subscribe.return_value = None

            response = client.post(
                "/v1/market/subscribe",
                json=["RELIANCE", "TCS", "INFY"],
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data['success'] is True
            assert len(data['data']['subscribed_symbols']) == 3

    async def test_get_market_movers_endpoint(self, client, auth_headers):
        """Test the market movers API endpoint"""
        mock_quotes = {
            'RELIANCE': {'symbol': 'RELIANCE', 'price': 2500.75, 'change': 25.50, 'change_percent': 1.03},
            'TCS': {'symbol': 'TCS', 'price': 3500.25, 'change': -50.25, 'change_percent': -1.41},
            'INFY': {'symbol': 'INFY', 'price': 1675.80, 'change': 35.90, 'change_percent': 2.19}
        }
        
        with patch.object(live_market_data_service, 'get_live_quote') as mock_get_quote:
            def mock_quote_side_effect(symbol, exchange):
                return mock_quotes.get(symbol)
            
            mock_get_quote.side_effect = mock_quote_side_effect

            response = client.get("/v1/market/market-movers", headers=auth_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data['success'] is True
            assert 'top_gainers' in data['data']
            assert 'top_losers' in data['data']

    async def test_market_data_health_endpoint(self, client):
        """Test the market data health check endpoint"""
        with patch.object(live_market_data_service, 'get_live_quote') as mock_get_quote:
            mock_get_quote.return_value = {'symbol': 'RELIANCE', 'price': 2500.75}

            response = client.get("/v1/market/health")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data['success'] is True
            assert data['data']['service_status'] == 'healthy'
            assert data['data']['test_quote_available'] is True

    async def test_unauthorized_access(self, client):
        """Test that endpoints require authentication"""
        response = client.get("/v1/market/quote/RELIANCE")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_batch_quotes_rate_limiting(self, client, auth_headers):
        """Test that batch quotes enforces symbol limits"""
        # Try to request more than 50 symbols
        symbols = [f"SYMBOL{i}" for i in range(51)]
        params = "&".join([f"symbols={symbol}" for symbol in symbols])
        
        response = client.get(f"/v1/market/quotes/batch?{params}", headers=auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_invalid_period_historical_data(self, client, auth_headers):
        """Test historical data with invalid period"""
        response = client.get(
            "/v1/market/historical/RELIANCE?period=invalid",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST