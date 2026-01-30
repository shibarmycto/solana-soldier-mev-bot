#!/usr/bin/env python3
"""
Solana Soldier Backend API Testing Suite
Tests all API endpoints for the Telegram bot backend
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Tuple

class SolanaSoldierAPITester:
    def __init__(self, base_url: str = "https://cryptoarb-6.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
    def log_test(self, name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            
        result = {
            "test_name": name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    Details: {details}")
        if not success and response_data:
            print(f"    Response: {response_data}")
        print()

    def test_api_endpoint(self, endpoint: str, method: str = "GET", 
                         expected_status: int = 200, data: Dict = None,
                         test_name: str = None) -> Tuple[bool, Any]:
        """Test a single API endpoint"""
        if not test_name:
            test_name = f"{method} {endpoint}"
            
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            else:
                self.log_test(test_name, False, f"Unsupported method: {method}")
                return False, None
                
            success = response.status_code == expected_status
            response_data = None
            
            try:
                response_data = response.json()
            except:
                response_data = response.text
                
            if success:
                self.log_test(test_name, True, f"Status: {response.status_code}", response_data)
            else:
                self.log_test(test_name, False, 
                            f"Expected {expected_status}, got {response.status_code}", 
                            response_data)
                
            return success, response_data
            
        except requests.exceptions.RequestException as e:
            self.log_test(test_name, False, f"Request failed: {str(e)}")
            return False, None
        except Exception as e:
            self.log_test(test_name, False, f"Unexpected error: {str(e)}")
            return False, None

    def test_root_endpoint(self):
        """Test /api/ endpoint returns status online"""
        success, data = self.test_api_endpoint("/", test_name="Root API Status")
        if success and data:
            if isinstance(data, dict) and data.get('status') == 'online':
                self.log_test("Root API Status Validation", True, "Status is 'online'")
            else:
                self.log_test("Root API Status Validation", False, 
                            f"Expected status 'online', got: {data}")

    def test_stats_endpoint(self):
        """Test /api/stats returns user statistics"""
        success, data = self.test_api_endpoint("/stats", test_name="Stats Endpoint")
        if success and data:
            required_fields = ['total_users', 'active_wallets', 'total_trades', 
                             'total_profit_usd', 'whale_activities_today']
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                self.log_test("Stats Fields Validation", True, 
                            f"All required fields present: {required_fields}")
            else:
                self.log_test("Stats Fields Validation", False, 
                            f"Missing fields: {missing_fields}")

    def test_whales_endpoint(self):
        """Test /api/whales returns list of tracked whale wallets"""
        success, data = self.test_api_endpoint("/whales", test_name="Whales Endpoint")
        if success and data:
            if isinstance(data, dict) and 'whales' in data:
                whales = data['whales']
                if isinstance(whales, list) and len(whales) > 0:
                    self.log_test("Whales Data Validation", True, 
                                f"Found {len(whales)} whale wallets")
                else:
                    self.log_test("Whales Data Validation", False, 
                                "No whale wallets found or invalid format")
            else:
                self.log_test("Whales Data Validation", False, 
                            "Response missing 'whales' field")

    def test_sol_price_endpoint(self):
        """Test /api/sol-price returns current SOL price"""
        success, data = self.test_api_endpoint("/sol-price", test_name="SOL Price Endpoint")
        if success and data:
            if isinstance(data, dict) and 'price_usd' in data:
                price = data['price_usd']
                if isinstance(price, (int, float)) and price > 0:
                    self.log_test("SOL Price Validation", True, 
                                f"SOL price: ${price}")
                else:
                    self.log_test("SOL Price Validation", False, 
                                f"Invalid price value: {price}")
            else:
                self.log_test("SOL Price Validation", False, 
                            "Response missing 'price_usd' field")

    def test_users_endpoint(self):
        """Test /api/users returns user list"""
        success, data = self.test_api_endpoint("/users", test_name="Users Endpoint")
        if success and data:
            if isinstance(data, dict) and 'users' in data:
                users = data['users']
                if isinstance(users, list):
                    self.log_test("Users Data Validation", True, 
                                f"Found {len(users)} users")
                else:
                    self.log_test("Users Data Validation", False, 
                                "Users field is not a list")
            else:
                self.log_test("Users Data Validation", False, 
                            "Response missing 'users' field")

    def test_trades_endpoint(self):
        """Test /api/trades returns trades list"""
        success, data = self.test_api_endpoint("/trades", test_name="Trades Endpoint")
        if success and data:
            if isinstance(data, dict) and 'trades' in data:
                trades = data['trades']
                if isinstance(trades, list):
                    self.log_test("Trades Data Validation", True, 
                                f"Found {len(trades)} trades")
                else:
                    self.log_test("Trades Data Validation", False, 
                                "Trades field is not a list")
            else:
                self.log_test("Trades Data Validation", False, 
                            "Response missing 'trades' field")

    def test_payments_endpoint(self):
        """Test /api/payments returns payments list"""
        success, data = self.test_api_endpoint("/payments", test_name="Payments Endpoint")
        if success and data:
            if isinstance(data, dict) and 'payments' in data:
                payments = data['payments']
                if isinstance(payments, list):
                    self.log_test("Payments Data Validation", True, 
                                f"Found {len(payments)} payments")
                else:
                    self.log_test("Payments Data Validation", False, 
                                "Payments field is not a list")
            else:
                self.log_test("Payments Data Validation", False, 
                            "Response missing 'payments' field")

    def test_whale_activities_endpoint(self):
        """Test /api/whale-activities endpoint"""
        success, data = self.test_api_endpoint("/whale-activities", 
                                             test_name="Whale Activities Endpoint")
        if success and data:
            if isinstance(data, dict) and 'activities' in data:
                activities = data['activities']
                if isinstance(activities, list):
                    self.log_test("Whale Activities Validation", True, 
                                f"Found {len(activities)} whale activities")
                else:
                    self.log_test("Whale Activities Validation", False, 
                                "Activities field is not a list")
            else:
                self.log_test("Whale Activities Validation", False, 
                            "Response missing 'activities' field")

    def test_trending_tokens_endpoint(self):
        """Test /api/trending-tokens endpoint"""
        success, data = self.test_api_endpoint("/trending-tokens", 
                                             test_name="Trending Tokens Endpoint")
        if success and data:
            if isinstance(data, dict) and 'tokens' in data:
                tokens = data['tokens']
                if isinstance(tokens, list):
                    self.log_test("Trending Tokens Validation", True, 
                                f"Found {len(tokens)} trending tokens")
                else:
                    self.log_test("Trending Tokens Validation", False, 
                                "Tokens field is not a list")
            else:
                self.log_test("Trending Tokens Validation", False, 
                            "Response missing 'tokens' field")

    def test_trading_stats_endpoint(self):
        """Test /api/trading-stats endpoint"""
        success, data = self.test_api_endpoint("/trading-stats", 
                                             test_name="Trading Stats Endpoint")
        if success and data:
            required_fields = ['min_profit_target', 'max_trade_time_seconds', 
                             'total_trades', 'success_rate']
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                self.log_test("Trading Stats Validation", True, 
                            f"All required fields present. Profit target: ${data.get('min_profit_target')}, Max time: {data.get('max_trade_time_seconds')}s")
            else:
                self.log_test("Trading Stats Validation", False, 
                            f"Missing fields: {missing_fields}")

    def test_rugcheck_endpoint(self):
        """Test /api/rugcheck/{token} endpoint"""
        # Test with WSOL address
        test_token = "So11111111111111111111111111111111111111112"
        success, data = self.test_api_endpoint(f"/rugcheck/{test_token}", 
                                             method="POST",
                                             test_name="Rugcheck Endpoint")
        if success and data:
            required_fields = ['token_address', 'is_safe', 'risk_score', 'warnings']
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                safety_status = "SAFE" if data.get('is_safe') else "RISKY"
                risk_score = data.get('risk_score', 0) * 100
                self.log_test("Rugcheck Validation", True, 
                            f"Token check complete. Status: {safety_status}, Risk: {risk_score:.0f}%")
            else:
                self.log_test("Rugcheck Validation", False, 
                            f"Missing fields: {missing_fields}")

    def test_system_status_endpoint(self):
        """Test /api/system-status endpoint - Phase 3 feature"""
        success, data = self.test_api_endpoint("/system-status", 
                                             test_name="System Status Endpoint")
        if success and data:
            # Check required Phase 3 fields
            required_fields = ['live_trading_enabled', 'auto_trade_on_whale_signal', 
                             'helius_rpc_connected', 'whale_monitor_active']
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                live_trading = data.get('live_trading_enabled')
                auto_trade = data.get('auto_trade_on_whale_signal')
                helius_connected = data.get('helius_rpc_connected')
                whale_monitor = data.get('whale_monitor_active')
                
                # Verify Phase 3 requirements
                if live_trading and auto_trade and helius_connected and whale_monitor:
                    self.log_test("System Status Phase 3 Validation", True, 
                                f"Live Trading: {live_trading}, Auto-Trade: {auto_trade}, Helius: {helius_connected}, Whale Monitor: {whale_monitor}")
                else:
                    self.log_test("System Status Phase 3 Validation", False, 
                                f"Phase 3 requirements not met - Live Trading: {live_trading}, Auto-Trade: {auto_trade}, Helius: {helius_connected}, Whale Monitor: {whale_monitor}")
            else:
                self.log_test("System Status Validation", False, 
                            f"Missing fields: {missing_fields}")

    def test_wallet_balance_endpoint(self):
        """Test /api/wallet-balance/{address} endpoint - Phase 3 Helius integration"""
        # Test with a known Solana address (WSOL mint)
        test_address = "So11111111111111111111111111111111111111112"
        success, data = self.test_api_endpoint(f"/wallet-balance/{test_address}", 
                                             test_name="Wallet Balance Endpoint")
        if success and data:
            required_fields = ['address', 'balance_sol']
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                address = data.get('address')
                balance = data.get('balance_sol')
                if address == test_address and isinstance(balance, (int, float)):
                    self.log_test("Wallet Balance Validation", True, 
                                f"Address: {address[:8]}..., Balance: {balance} SOL")
                else:
                    self.log_test("Wallet Balance Validation", False, 
                                f"Invalid response - Address: {address}, Balance: {balance}")
            else:
                self.log_test("Wallet Balance Validation", False, 
                            f"Missing fields: {missing_fields}")

    def test_trading_stats_phase3(self):
        """Test /api/trading-stats endpoint for Phase 3 fields"""
        success, data = self.test_api_endpoint("/trading-stats", 
                                             test_name="Trading Stats Phase 3 Check")
        if success and data:
            # Check for Phase 3 specific fields
            phase3_fields = ['live_trading_enabled', 'auto_trade_enabled']
            found_fields = [field for field in phase3_fields if field in data]
            
            if len(found_fields) == len(phase3_fields):
                live_enabled = data.get('live_trading_enabled')
                auto_enabled = data.get('auto_trade_enabled')
                self.log_test("Trading Stats Phase 3 Fields", True, 
                            f"Live Trading: {live_enabled}, Auto Trade: {auto_enabled}")
            else:
                missing = [field for field in phase3_fields if field not in data]
                self.log_test("Trading Stats Phase 3 Fields", False, 
                            f"Missing Phase 3 fields: {missing}")

    def run_all_tests(self):
        """Run all backend API tests"""
        print("🚀 Starting Solana Soldier Backend API Tests")
        print("=" * 60)
        print()
        
        # Test all required endpoints
        self.test_root_endpoint()
        self.test_stats_endpoint()
        self.test_whales_endpoint()
        self.test_sol_price_endpoint()
        self.test_users_endpoint()
        self.test_trades_endpoint()
        self.test_payments_endpoint()
        
        # Phase 2 endpoints
        self.test_whale_activities_endpoint()
        self.test_trending_tokens_endpoint()
        self.test_trading_stats_endpoint()
        self.test_rugcheck_endpoint()
        
        # Phase 3 endpoints
        self.test_system_status_endpoint()
        self.test_wallet_balance_endpoint()
        self.test_trading_stats_phase3()
        
        # Print summary
        print("=" * 60)
        print(f"📊 TEST SUMMARY")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        print()
        
        # Return success if all critical tests pass
        critical_tests = [
            "Root API Status", "Stats Endpoint", "Whales Endpoint", 
            "SOL Price Endpoint", "Users Endpoint", "Trades Endpoint", 
            "Payments Endpoint", "Trading Stats Endpoint", "Rugcheck Endpoint"
        ]
        
        critical_passed = sum(1 for result in self.test_results 
                            if result['test_name'] in critical_tests and result['success'])
        
        if critical_passed == len(critical_tests):
            print("✅ All critical API endpoints are working!")
            return 0
        else:
            print(f"❌ {len(critical_tests) - critical_passed} critical endpoints failed!")
            return 1

def main():
    """Main test runner"""
    tester = SolanaSoldierAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())