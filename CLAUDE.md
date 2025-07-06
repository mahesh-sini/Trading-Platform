# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered trading platform with microservices architecture built for SaaS delivery. The platform provides automated trading, ML-powered predictions, and real-time market data processing.

## Development Environment Setup

### Environment Activation
```bash
# Initial setup (run once)
./setup.sh

# Activate development environment
source activate_env.sh

# Deactivate when done
deactivate
```

### Key Dependencies
- Python 3.12+ with virtual environment in `trading_env/`
- FastAPI for backend services
- React for frontend (planned)
- PostgreSQL, InfluxDB, Redis for data storage
- Kafka/RabbitMQ for message queuing
- ML libraries: scikit-learn, TensorFlow/PyTorch

### Environment Variables
Required in `.env` file:
- `ANTHROPIC_API_KEY`: For Claude CLI integration

## Common Commands

### Development
```bash
# Use Claude CLI for development assistance
python claude_cli.py "your prompt here"

# With conversation context
python claude_cli.py --context conversations/claude_conversation_20250703_202225.json "follow up question"
```

### Testing and Quality
No specific test commands are configured yet. When implementing:
- Add test framework (pytest recommended for Python)
- Add linting tools (ruff/black for Python)
- Add type checking (mypy for Python)

## Architecture Overview

### Core Services Structure
- **backend/**: FastAPI microservices
  - `api/`: REST API endpoints
  - `models/`: Database models and schemas
  - `services/`: Business logic and external integrations
  - `utils/`: Shared utilities and helpers
- **frontend/**: React dashboard (planned)
- **ml_models/**: Machine learning components
  - `training/`: Model training pipelines
  - `prediction/`: Inference and prediction services
  - `data_processing/`: Feature engineering and data pipelines
- **data/**: Data storage and processing
- **tests/`: Test suites

### Key Architectural Patterns
- **Microservices**: Separate services for user auth, trading, ML, and data
- **Event-Driven**: Message queue (Kafka/RabbitMQ) for service communication
- **Real-time Processing**: WebSocket connections for live market data
- **Multi-Database**: PostgreSQL (transactional), InfluxDB (time series), Redis (caching)

### Performance Requirements
- Trade execution: <50ms end-to-end
- Market data updates: <100ms
- ML predictions: <200ms
- API responses: <500ms (95th percentile)

## Development Workflow

### Project Structure Creation
Use the Claude CLI with prompts from `claude_commands.txt` for guided development:
- Backend API development with FastAPI
- Database models and schema design
- ML model implementation and training
- Frontend React dashboard creation
- DevOps and deployment setup

### Code Conventions
- Follow existing patterns in the codebase
- Use Python type hints and FastAPI's dependency injection
- Implement proper error handling and logging
- Add comprehensive tests for all new features
- Document APIs using FastAPI's automatic documentation

## Integration Points

### Broker APIs
- Alpaca, Interactive Brokers, TD Ameritrade
- Real-time market data feeds
- Order execution and portfolio management

### External Data Sources
- Yahoo Finance, Alpha Vantage, Polygon.io
- News APIs and sentiment analysis
- Social media data for sentiment scoring

## Security Considerations
- JWT tokens for authentication
- Encrypted API keys and credentials
- Rate limiting and request validation
- Audit logging for all trading activities
- GDPR and financial regulation compliance