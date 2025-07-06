#!/usr/bin/env python3
"""
API Credentials Setup Script
Interactive setup for Indian broker and market data API credentials
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class APICredentialsSetup:
    """Interactive setup for API credentials"""
    
    def __init__(self):
        self.env_file = Path(".env")
        self.credentials = {}
        self.existing_env = self._load_existing_env()
        
    def _load_existing_env(self) -> Dict[str, str]:
        """Load existing environment variables"""
        env_vars = {}
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key] = value.strip('"\'')
        return env_vars
    
    def print_header(self):
        """Print setup header"""
        print("\n" + "="*70)
        print("🔑 AI Trading Platform - API Credentials Setup")
        print("="*70)
        print("This script will help you configure API credentials for:")
        print("• Indian broker APIs (Upstox, Zerodha, ICICI, Angel One)")
        print("• Market data providers (Alpha Vantage, Polygon)")
        print("• Real-time data access for production trading")
        print("="*70)
    
    def print_provider_info(self, provider: str, info: Dict[str, str]):
        """Print provider information"""
        print(f"\n📊 {provider.upper()}")
        print("-" * 50)
        for key, value in info.items():
            print(f"  {key}: {value}")
    
    def get_user_input(self, prompt: str, current_value: str = "", is_secret: bool = False) -> str:
        """Get user input with current value display"""
        if current_value:
            display_value = "***HIDDEN***" if is_secret else current_value
            prompt += f" (current: {display_value})"
        
        prompt += ": "
        value = input(prompt).strip()
        
        # Return current value if user just presses enter
        if not value and current_value:
            return current_value
        
        return value
    
    def setup_free_apis(self):
        """Setup free API providers"""
        print("\n🆓 FREE API PROVIDERS")
        print("=" * 50)
        
        # Alpha Vantage (free tier)
        self.print_provider_info("Alpha Vantage", {
            "Cost": "FREE tier (5 req/min, 500 req/day)",
            "Paid": "$49.99/month for 75 req/min",
            "URL": "https://www.alphavantage.co/support/#api-key",
            "Coverage": "Global markets including Indian stocks"
        })
        
        if input("\n🔧 Setup Alpha Vantage? (y/n): ").lower() == 'y':
            api_key = self.get_user_input(
                "Enter Alpha Vantage API Key",
                self.existing_env.get('ALPHA_VANTAGE_API_KEY', ''),
                is_secret=True
            )
            if api_key:
                self.credentials['ALPHA_VANTAGE_API_KEY'] = api_key
                print("✅ Alpha Vantage configured")
        
        # Polygon.io
        self.print_provider_info("Polygon.io", {
            "Cost": "FREE tier (limited historical data)",
            "Paid": "$99/month for real-time US markets",
            "URL": "https://polygon.io",
            "Coverage": "Primarily US markets, limited Indian coverage"
        })
        
        if input("\n🔧 Setup Polygon.io? (y/n): ").lower() == 'y':
            api_key = self.get_user_input(
                "Enter Polygon API Key",
                self.existing_env.get('POLYGON_API_KEY', ''),
                is_secret=True
            )
            if api_key:
                self.credentials['POLYGON_API_KEY'] = api_key
                print("✅ Polygon.io configured")
    
    def setup_indian_brokers(self):
        """Setup Indian broker APIs"""
        print("\n🇮🇳 INDIAN BROKER APIs")
        print("=" * 50)
        
        # Upstox
        self.print_provider_info("Upstox", {
            "Cost": "FREE with trading account",
            "Requirements": "Upstox trading account + API registration",
            "URL": "https://upstox.com/developer",
            "Coverage": "NSE, BSE real-time data"
        })
        
        if input("\n🔧 Setup Upstox? (y/n): ").lower() == 'y':
            api_key = self.get_user_input(
                "Enter Upstox API Key",
                self.existing_env.get('UPSTOX_API_KEY', ''),
                is_secret=True
            )
            secret = self.get_user_input(
                "Enter Upstox Secret",
                self.existing_env.get('UPSTOX_SECRET', ''),
                is_secret=True
            )
            access_token = self.get_user_input(
                "Enter Upstox Access Token (optional)",
                self.existing_env.get('UPSTOX_ACCESS_TOKEN', ''),
                is_secret=True
            )
            
            if api_key and secret:
                self.credentials['UPSTOX_API_KEY'] = api_key
                self.credentials['UPSTOX_SECRET'] = secret
                if access_token:
                    self.credentials['UPSTOX_ACCESS_TOKEN'] = access_token
                print("✅ Upstox configured")
        
        # Zerodha
        self.print_provider_info("Zerodha Kite", {
            "Cost": "₹2,000/month for API access",
            "Requirements": "Zerodha trading account + API subscription",
            "URL": "https://kite.trade",
            "Coverage": "NSE, BSE, MCX, NCDEX"
        })
        
        if input("\n🔧 Setup Zerodha? (y/n): ").lower() == 'y':
            api_key = self.get_user_input(
                "Enter Zerodha API Key",
                self.existing_env.get('ZERODHA_API_KEY', ''),
                is_secret=True
            )
            secret = self.get_user_input(
                "Enter Zerodha Secret",
                self.existing_env.get('ZERODHA_SECRET', ''),
                is_secret=True
            )
            access_token = self.get_user_input(
                "Enter Zerodha Access Token (optional)",
                self.existing_env.get('ZERODHA_ACCESS_TOKEN', ''),
                is_secret=True
            )
            
            if api_key and secret:
                self.credentials['ZERODHA_API_KEY'] = api_key
                self.credentials['ZERODHA_SECRET'] = secret
                if access_token:
                    self.credentials['ZERODHA_ACCESS_TOKEN'] = access_token
                print("✅ Zerodha configured")
        
        # ICICI Breeze
        self.print_provider_info("ICICI Breeze", {
            "Cost": "FREE with ICICI Direct account",
            "Requirements": "ICICI Direct trading account",
            "URL": "https://www.icicidirect.com/apiuser",
            "Coverage": "NSE, BSE"
        })
        
        if input("\n🔧 Setup ICICI Breeze? (y/n): ").lower() == 'y':
            api_key = self.get_user_input(
                "Enter ICICI Breeze API Key",
                self.existing_env.get('ICICI_BREEZE_API_KEY', ''),
                is_secret=True
            )
            secret = self.get_user_input(
                "Enter ICICI Breeze Secret",
                self.existing_env.get('ICICI_BREEZE_SECRET', ''),
                is_secret=True
            )
            session_token = self.get_user_input(
                "Enter ICICI Session Token (optional)",
                self.existing_env.get('ICICI_BREEZE_SESSION_TOKEN', ''),
                is_secret=True
            )
            
            if api_key and secret:
                self.credentials['ICICI_BREEZE_API_KEY'] = api_key
                self.credentials['ICICI_BREEZE_SECRET'] = secret
                if session_token:
                    self.credentials['ICICI_BREEZE_SESSION_TOKEN'] = session_token
                print("✅ ICICI Breeze configured")
        
        # Angel One
        self.print_provider_info("Angel One SmartAPI", {
            "Cost": "FREE with Angel One account",
            "Requirements": "Angel One trading account",
            "URL": "https://smartapi.angelbroking.com",
            "Coverage": "NSE, BSE, MCX"
        })
        
        if input("\n🔧 Setup Angel One? (y/n): ").lower() == 'y':
            api_key = self.get_user_input(
                "Enter Angel One API Key",
                self.existing_env.get('ANGEL_ONE_API_KEY', ''),
                is_secret=True
            )
            client_id = self.get_user_input(
                "Enter Angel One Client ID",
                self.existing_env.get('ANGEL_ONE_CLIENT_ID', '')
            )
            password = self.get_user_input(
                "Enter Angel One Password",
                self.existing_env.get('ANGEL_ONE_PASSWORD', ''),
                is_secret=True
            )
            jwt_token = self.get_user_input(
                "Enter Angel One JWT Token (optional)",
                self.existing_env.get('ANGEL_ONE_JWT_TOKEN', ''),
                is_secret=True
            )
            
            if api_key and client_id:
                self.credentials['ANGEL_ONE_API_KEY'] = api_key
                self.credentials['ANGEL_ONE_CLIENT_ID'] = client_id
                if password:
                    self.credentials['ANGEL_ONE_PASSWORD'] = password
                if jwt_token:
                    self.credentials['ANGEL_ONE_JWT_TOKEN'] = jwt_token
                print("✅ Angel One configured")
    
    def save_credentials(self):
        """Save credentials to .env file"""
        try:
            # Merge with existing credentials
            all_credentials = {**self.existing_env, **self.credentials}
            
            # Write to .env file
            with open(self.env_file, 'w') as f:
                f.write("# AI Trading Platform - API Credentials\n")
                f.write("# Generated by setup_api_credentials.py\n\n")
                
                if any(key.startswith('ALPHA_VANTAGE') or key.startswith('POLYGON') for key in all_credentials):
                    f.write("# Market Data Providers\n")
                    for key in ['ALPHA_VANTAGE_API_KEY', 'POLYGON_API_KEY']:
                        if key in all_credentials:
                            f.write(f"{key}={all_credentials[key]}\n")
                    f.write("\n")
                
                if any(key.startswith('UPSTOX') for key in all_credentials):
                    f.write("# Upstox API\n")
                    for key in ['UPSTOX_API_KEY', 'UPSTOX_SECRET', 'UPSTOX_ACCESS_TOKEN']:
                        if key in all_credentials:
                            f.write(f"{key}={all_credentials[key]}\n")
                    f.write("\n")
                
                if any(key.startswith('ZERODHA') for key in all_credentials):
                    f.write("# Zerodha Kite API\n")
                    for key in ['ZERODHA_API_KEY', 'ZERODHA_SECRET', 'ZERODHA_ACCESS_TOKEN']:
                        if key in all_credentials:
                            f.write(f"{key}={all_credentials[key]}\n")
                    f.write("\n")
                
                if any(key.startswith('ICICI') for key in all_credentials):
                    f.write("# ICICI Breeze API\n")
                    for key in ['ICICI_BREEZE_API_KEY', 'ICICI_BREEZE_SECRET', 'ICICI_BREEZE_SESSION_TOKEN']:
                        if key in all_credentials:
                            f.write(f"{key}={all_credentials[key]}\n")
                    f.write("\n")
                
                if any(key.startswith('ANGEL_ONE') for key in all_credentials):
                    f.write("# Angel One SmartAPI\n")
                    for key in ['ANGEL_ONE_API_KEY', 'ANGEL_ONE_CLIENT_ID', 'ANGEL_ONE_PASSWORD', 'ANGEL_ONE_JWT_TOKEN']:
                        if key in all_credentials:
                            f.write(f"{key}={all_credentials[key]}\n")
                    f.write("\n")
                
                # Add other environment variables
                other_vars = {k: v for k, v in all_credentials.items() 
                            if not any(k.startswith(prefix) for prefix in 
                                     ['ALPHA_VANTAGE', 'POLYGON', 'UPSTOX', 'ZERODHA', 'ICICI', 'ANGEL_ONE'])}
                
                if other_vars:
                    f.write("# Other Environment Variables\n")
                    for key, value in other_vars.items():
                        f.write(f"{key}={value}\n")
            
            print(f"\n✅ Credentials saved to {self.env_file}")
            return True
            
        except Exception as e:
            print(f"\n❌ Error saving credentials: {e}")
            return False
    
    def test_credentials(self):
        """Test API credentials"""
        print("\n🧪 TESTING API CREDENTIALS")
        print("=" * 50)
        
        if not self.credentials:
            print("⚠️  No new credentials to test")
            return
        
        # Test each configured provider
        test_results = {}
        
        # Simple validation tests
        for key, value in self.credentials.items():
            if not value or len(value) < 10:
                test_results[key] = "❌ Invalid format (too short)"
            else:
                test_results[key] = "✅ Format valid"
        
        print("\n📋 Credential Validation Results:")
        for key, result in test_results.items():
            print(f"  {key}: {result}")
        
        print("\n💡 For full API testing, run the market data service")
        print("   and check the monitoring dashboard for provider status.")
    
    def print_summary(self):
        """Print setup summary"""
        print("\n🎉 API CREDENTIALS SETUP COMPLETE")
        print("=" * 70)
        
        configured_count = len(self.credentials)
        total_possible = 11  # Total possible credentials
        
        print(f"📊 Configured: {configured_count} credentials")
        
        if configured_count > 0:
            print("\n✅ Successfully configured:")
            for key in self.credentials.keys():
                provider = key.split('_')[0].title()
                print(f"   • {provider}")
        
        print(f"\n📁 Configuration saved to: {self.env_file}")
        
        print("\n🚀 Next Steps:")
        print("   1. Restart your application to load new credentials")
        print("   2. Run 'python setup_monitoring.py' to verify API connectivity")
        print("   3. Check the monitoring dashboard for provider status")
        print("   4. Test live market data in your trading dashboard")
        
        print("\n📖 Documentation:")
        print("   • API setup guide: API_CREDENTIALS_GUIDE.md")
        print("   • Monitoring docs: backend/monitoring/")
        
        if configured_count == 0:
            print("\n⚠️  No credentials configured. You can:")
            print("   • Re-run this script anytime: python setup_api_credentials.py")
            print("   • Manually edit the .env file")
            print("   • Use free APIs (NSE, Yahoo Finance) without configuration")
    
    def run_setup(self):
        """Run the complete setup process"""
        self.print_header()
        
        # Setup free APIs
        self.setup_free_apis()
        
        # Setup Indian broker APIs
        self.setup_indian_brokers()
        
        # Save credentials
        if self.credentials:
            if self.save_credentials():
                self.test_credentials()
            else:
                print("❌ Failed to save credentials. Setup incomplete.")
                return False
        
        # Print summary
        self.print_summary()
        return True

def main():
    """Main setup function"""
    try:
        setup = APICredentialsSetup()
        
        # Check if running in interactive mode
        if not sys.stdin.isatty():
            print("❌ This script requires interactive input. Run it in a terminal.")
            return 1
        
        # Run setup
        success = setup.run_setup()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n👋 Setup cancelled by user")
        return 0
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())