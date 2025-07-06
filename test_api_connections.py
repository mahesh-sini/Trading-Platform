#!/usr/bin/env python3
"""
API Connection Test Script
Tests all configured API providers and generates a connectivity report
"""

import asyncio
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from services.live_market_data import LiveMarketDataService
from services.indian_broker_apis import IndianBrokerAPIService

class APIConnectionTester:
    """Test API connections and generate connectivity report"""
    
    def __init__(self):
        self.test_symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK']
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def print_header(self):
        """Print test header"""
        print("\n" + "="*70)
        print("🧪 AI Trading Platform - API Connection Test")
        print("="*70)
        print("Testing connectivity to all configured market data providers...")
        print(f"Test symbols: {', '.join(self.test_symbols)}")
        print("="*70)
    
    async def test_live_market_data_service(self) -> Dict[str, Any]:
        """Test the main live market data service"""
        print("\n📊 Testing Live Market Data Service...")
        
        service_results = {
            'service_name': 'Live Market Data Service',
            'providers_tested': [],
            'successful_quotes': 0,
            'failed_quotes': 0,
            'total_tests': 0,
            'average_latency': 0.0,
            'errors': []
        }
        
        try:
            service = LiveMarketDataService()
            
            total_latency = 0.0
            successful_tests = 0
            
            for symbol in self.test_symbols:
                print(f"  Testing {symbol}...")
                
                start_time = time.time()
                try:
                    quote = await service.get_live_quote(symbol, 'NSE')
                    latency = time.time() - start_time
                    total_latency += latency
                    
                    if quote:
                        successful_tests += 1
                        service_results['successful_quotes'] += 1
                        provider = quote.get('provider', 'unknown')
                        if provider not in service_results['providers_tested']:
                            service_results['providers_tested'].append(provider)
                        print(f"    ✅ Success (provider: {provider}, latency: {latency:.3f}s)")
                    else:
                        service_results['failed_quotes'] += 1
                        print(f"    ❌ No data returned")
                        
                except Exception as e:
                    service_results['failed_quotes'] += 1
                    service_results['errors'].append(f"{symbol}: {str(e)}")
                    print(f"    ❌ Error: {str(e)}")
                
                service_results['total_tests'] += 1
                
                # Small delay between requests
                await asyncio.sleep(0.5)
            
            if successful_tests > 0:
                service_results['average_latency'] = total_latency / successful_tests
            
            await service.close()
            
        except Exception as e:
            service_results['errors'].append(f"Service initialization error: {str(e)}")
            print(f"    ❌ Service error: {str(e)}")
        
        return service_results
    
    async def test_indian_broker_apis(self) -> Dict[str, Any]:
        """Test Indian broker APIs individually"""
        print("\n🇮🇳 Testing Indian Broker APIs...")
        
        broker_results = {
            'service_name': 'Indian Broker APIs',
            'providers_tested': [],
            'provider_results': {},
            'total_providers': 0,
            'working_providers': 0,
            'errors': []
        }
        
        try:
            broker_service = IndianBrokerAPIService()
            available_providers = broker_service.get_available_providers()
            
            broker_results['total_providers'] = len(available_providers)
            
            if not available_providers:
                print("  ⚠️  No Indian broker APIs configured")
                broker_results['errors'].append("No Indian broker APIs configured")
                return broker_results
            
            for provider in available_providers:
                print(f"  Testing {provider.upper()}...")
                broker_results['providers_tested'].append(provider)
                
                provider_result = {
                    'successful_quotes': 0,
                    'failed_quotes': 0,
                    'total_tests': 0,
                    'average_latency': 0.0,
                    'errors': []
                }
                
                total_latency = 0.0
                successful_tests = 0
                
                # Test one symbol for each provider
                test_symbol = 'RELIANCE'
                
                try:
                    start_time = time.time()
                    
                    if provider == 'upstox':
                        quote = await broker_service.get_upstox_quote(test_symbol)
                    elif provider == 'zerodha':
                        quote = await broker_service.get_zerodha_quote(test_symbol)
                    elif provider == 'icici':
                        quote = await broker_service.get_icici_quote(test_symbol)
                    elif provider == 'angel_one':
                        quote = await broker_service.get_angel_one_quote(test_symbol)
                    else:
                        quote = None
                    
                    latency = time.time() - start_time
                    total_latency += latency
                    
                    if quote:
                        successful_tests += 1
                        provider_result['successful_quotes'] += 1
                        print(f"    ✅ Success (latency: {latency:.3f}s)")
                        broker_results['working_providers'] += 1
                    else:
                        provider_result['failed_quotes'] += 1
                        print(f"    ❌ No data returned")
                    
                except Exception as e:
                    provider_result['failed_quotes'] += 1
                    provider_result['errors'].append(str(e))
                    print(f"    ❌ Error: {str(e)}")
                
                provider_result['total_tests'] += 1
                if successful_tests > 0:
                    provider_result['average_latency'] = total_latency / successful_tests
                
                broker_results['provider_results'][provider] = provider_result
            
            await broker_service.close()
            
        except Exception as e:
            broker_results['errors'].append(f"Broker service error: {str(e)}")
            print(f"    ❌ Service error: {str(e)}")
        
        return broker_results
    
    async def test_free_apis(self) -> Dict[str, Any]:
        """Test free API providers"""
        print("\n🆓 Testing Free API Providers...")
        
        free_api_results = {
            'service_name': 'Free API Providers',
            'nse_direct': {'working': False, 'error': None},
            'yahoo_finance': {'working': False, 'error': None},
            'alpha_vantage': {'working': False, 'error': None},
            'polygon': {'working': False, 'error': None}
        }
        
        # Test through the main service which includes free APIs
        try:
            service = LiveMarketDataService()
            
            # Test a quote that should work with free APIs
            test_symbol = 'RELIANCE'
            quote = await service.get_live_quote(test_symbol, 'NSE')
            
            if quote:
                provider = quote.get('provider', 'unknown')
                print(f"  ✅ Free APIs working (provider: {provider})")
                
                # Mark the working provider
                if provider in free_api_results:
                    free_api_results[provider]['working'] = True
                elif provider in ['nse', 'yahoo_finance']:
                    free_api_results[provider]['working'] = True
            else:
                print("  ❌ Free APIs not working")
            
            await service.close()
            
        except Exception as e:
            print(f"  ❌ Error testing free APIs: {str(e)}")
            for provider in ['nse_direct', 'yahoo_finance']:
                free_api_results[provider]['error'] = str(e)
        
        return free_api_results
    
    def generate_report(self):
        """Generate a comprehensive test report"""
        print("\n📋 API CONNECTION TEST REPORT")
        print("="*70)
        
        total_duration = (self.end_time - self.start_time) if self.start_time and self.end_time else 0
        print(f"Test Duration: {total_duration:.2f} seconds")
        print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Summary statistics
        total_providers = 0
        working_providers = 0
        total_tests = 0
        successful_tests = 0
        
        for service_name, results in self.results.items():
            if isinstance(results, dict):
                if 'total_providers' in results:
                    total_providers += results['total_providers']
                    working_providers += results['working_providers']
                if 'total_tests' in results:
                    total_tests += results['total_tests']
                    successful_tests += results['successful_quotes']
        
        print(f"\n📊 SUMMARY")
        print(f"  Total Providers Configured: {total_providers}")
        print(f"  Working Providers: {working_providers}")
        print(f"  Success Rate: {(working_providers/total_providers*100):.1f}%" if total_providers > 0 else "  Success Rate: N/A")
        print(f"  Total API Tests: {total_tests}")
        print(f"  Successful Tests: {successful_tests}")
        
        # Detailed results
        for service_name, results in self.results.items():
            print(f"\n📋 {service_name.upper()}")
            print("-" * 50)
            
            if service_name == 'live_market_data':
                print(f"  Providers Used: {', '.join(results['providers_tested'])}")
                print(f"  Successful Quotes: {results['successful_quotes']}/{results['total_tests']}")
                print(f"  Average Latency: {results['average_latency']:.3f}s")
                if results['errors']:
                    print(f"  Errors: {len(results['errors'])}")
                    for error in results['errors'][:3]:  # Show first 3 errors
                        print(f"    • {error}")
            
            elif service_name == 'indian_brokers':
                print(f"  Configured Providers: {results['total_providers']}")
                print(f"  Working Providers: {results['working_providers']}")
                
                for provider, provider_results in results['provider_results'].items():
                    status = "✅" if provider_results['successful_quotes'] > 0 else "❌"
                    latency = f" ({provider_results['average_latency']:.3f}s)" if provider_results['average_latency'] > 0 else ""
                    print(f"    {status} {provider.upper()}{latency}")
            
            elif service_name == 'free_apis':
                for provider, provider_data in results.items():
                    if provider != 'service_name':
                        status = "✅" if provider_data['working'] else "❌"
                        print(f"    {status} {provider.upper()}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS")
        print("-" * 50)
        
        if working_providers == 0:
            print("  ⚠️  No API providers are working!")
            print("  • Check your API credentials in the .env file")
            print("  • Run 'python setup_api_credentials.py' to configure APIs")
            print("  • Verify your internet connection")
        elif working_providers < 2:
            print("  ⚠️  Limited API redundancy")
            print("  • Configure additional API providers for redundancy")
            print("  • Consider setting up Indian broker APIs for better coverage")
        else:
            print("  ✅ Good API coverage detected")
            print("  • Multiple providers configured for redundancy")
            print("  • System ready for production use")
        
        # Save report to file
        self.save_report_to_file()
    
    def save_report_to_file(self):
        """Save test report to JSON file"""
        try:
            report_data = {
                'test_timestamp': datetime.now().isoformat(),
                'test_duration': (self.end_time - self.start_time) if self.start_time and self.end_time else 0,
                'results': self.results
            }
            
            report_file = Path('api_test_report.json')
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            print(f"\n💾 Detailed report saved to: {report_file}")
            
        except Exception as e:
            print(f"\n❌ Failed to save report: {e}")
    
    async def run_tests(self):
        """Run all API connection tests"""
        self.start_time = time.time()
        
        # Test live market data service
        self.results['live_market_data'] = await self.test_live_market_data_service()
        
        # Test Indian broker APIs
        self.results['indian_brokers'] = await self.test_indian_broker_apis()
        
        # Test free APIs
        self.results['free_apis'] = await self.test_free_apis()
        
        self.end_time = time.time()
        
        # Generate report
        self.generate_report()

async def main():
    """Main test function"""
    try:
        tester = APIConnectionTester()
        tester.print_header()
        
        await tester.run_tests()
        
        print(f"\n🎉 API connection testing completed!")
        print(f"📊 Run 'python setup_monitoring.py' to start monitoring")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n👋 Testing cancelled by user")
        return 0
    except Exception as e:
        print(f"\n❌ Testing failed: {e}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)