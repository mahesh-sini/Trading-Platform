#!/bin/bash

# Trading Platform Development Setup Script
echo "🚀 Setting up Trading Platform Development Environment..."

# Check if we're in the right directory
if [[ ! "$PWD" =~ "Trading Platform" ]]; then
    echo "❌ Please run this script from your 'Trading Platform' directory"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv trading_env

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source trading_env/bin/activate

# Install required packages
echo "📥 Installing Python packages..."
pip install anthropic python-dotenv requests fastapi uvicorn numpy pandas scikit-learn

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "🔐 Creating .env file..."
    echo "ANTHROPIC_API_KEY=XbPwJIj4sfIKu5zJmGRdsyrC4sZwrrPtQI4s0Em2XmFrC6X3#R1vonkTdoNcMXx76jhjHIWadYT5QzYcBr_QR3X-AWR0" > .env
    echo "⚠️  Please edit .env file and add your actual API key"
fi

# Create project structure
echo "📁 Creating project structure..."
mkdir -p {backend,frontend,ml_models,data,conversations,tests}
mkdir -p backend/{api,models,services,utils}
mkdir -p frontend/{src,public,components}
mkdir -p ml_models/{training,prediction,data_processing}

# Create activation script
echo "📝 Creating activation script..."
cat > activate_env.sh << 'EOF'
#!/bin/bash
echo "🔄 Activating Trading Platform environment..."
source trading_env/bin/activate
echo "✅ Environment activated. You can now use:"
echo "   python claude_cli.py \"your prompt here\""
echo "   deactivate  # to exit the environment"
EOF

chmod +x activate_env.sh

# Create quick start commands
echo "📋 Creating quick start commands..."
cat > claude_commands.txt << 'EOF'
# Trading Platform Development Commands

# Project Setup
python claude_cli.py "Create the initial project structure and main files for our AI trading platform"

# Backend Development
python claude_cli.py "Help me implement the FastAPI backend with user authentication and broker API integration"
python claude_cli.py "Create database models for users, trades, and portfolio management"
python claude_cli.py "Implement the automated trading engine with risk management"

# Frontend Development
python claude_cli.py "Create a React trading dashboard with real-time price updates using WebSocket"
python claude_cli.py "Build a responsive trading interface with charts and order placement"

# ML Model Development
python claude_cli.py "Implement the ensemble ML model for stock price prediction"
python claude_cli.py "Create the data pipeline for processing market data and training models"

# DevOps & Deployment
python claude_cli.py "Set up Docker containers for the trading platform"
python claude_cli.py "Create CI/CD pipeline for automated deployment"
EOF

echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Edit .env file and add your ANTHROPIC_API_KEY"
echo "2. Run: source activate_env.sh"
echo "3. Test: python claude_cli.py \"Hello, help me start building the trading platform\""
echo "4. Check claude_commands.txt for useful commands"
echo ""
echo "💡 To activate the environment in the future:"
echo "   source activate_env.sh"