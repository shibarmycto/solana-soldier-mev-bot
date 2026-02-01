"""
Solana Soldier Bot - Backend API Tests
Tests all API endpoints for the Telegram-based Solana arbitrage trading bot
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthAndStatus:
    """Health check and system status endpoint tests"""
    
    def test_api_health_check(self):
        """Test /api/ returns online status"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "online"
        assert "message" in data
        print(f"✅ API health check passed: {data}")
    
    def test_system_status_endpoint(self):
        """Test /api/system-status returns correct trading configuration"""
        response = requests.get(f"{BASE_URL}/api/system-status")
        assert response.status_code == 200
        data = response.json()
        
        # Verify live trading is enabled
        assert data.get("live_trading_enabled") == True
        assert data.get("auto_trade_on_whale_signal") == True
        
        # Verify trading parameters
        assert data.get("min_profit_target_usd") == 2.0
        assert data.get("max_trade_time_seconds") == 120
        assert data.get("min_trade_sol") == 0.02
        assert data.get("max_trade_sol") == 0.5
        
        # Verify connections
        assert data.get("helius_rpc_connected") == True
        assert data.get("jupiter_dex_ready") == True
        assert data.get("whale_monitor_active") == True
        
        # Verify whale tracking
        assert data.get("tracked_whale_wallets") == 9
        
        print(f"✅ System status passed: live_trading={data.get('live_trading_enabled')}, whales={data.get('tracked_whale_wallets')}")


class TestTradingStats:
    """Trading statistics endpoint tests"""
    
    def test_trading_stats_endpoint(self):
        """Test /api/trading-stats returns trading statistics"""
        response = requests.get(f"{BASE_URL}/api/trading-stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields exist
        assert "total_trades" in data
        assert "trades_today" in data
        assert "total_profit_usd" in data
        assert "success_rate" in data
        assert "live_trading_enabled" in data
        assert "auto_trade_enabled" in data
        assert "tracked_whales" in data
        
        # Verify live trading is enabled
        assert data.get("live_trading_enabled") == True
        assert data.get("auto_trade_enabled") == True
        assert data.get("tracked_whales") == 9
        
        print(f"✅ Trading stats passed: trades={data.get('total_trades')}, profit=${data.get('total_profit_usd')}")
    
    def test_stats_endpoint(self):
        """Test /api/stats returns user statistics"""
        response = requests.get(f"{BASE_URL}/api/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "total_users" in data
        assert "active_wallets" in data
        assert "total_trades" in data
        assert "total_profit_usd" in data
        assert "whale_activities_today" in data
        
        print(f"✅ Stats passed: users={data.get('total_users')}, wallets={data.get('active_wallets')}")


class TestWhaleTracking:
    """Whale tracking endpoint tests"""
    
    def test_whales_endpoint(self):
        """Test /api/whales returns tracked whale wallets"""
        response = requests.get(f"{BASE_URL}/api/whales")
        assert response.status_code == 200
        data = response.json()
        
        assert "whales" in data
        whales = data.get("whales", [])
        assert len(whales) == 9  # 9 whale wallets configured
        
        # Verify wallet addresses are valid Solana addresses (32-50 chars)
        for wallet in whales:
            assert len(wallet) >= 32 and len(wallet) <= 50
        
        print(f"✅ Whales endpoint passed: {len(whales)} whale wallets tracked")
    
    def test_whale_activities_endpoint(self):
        """Test /api/whale-activities returns whale activity list"""
        response = requests.get(f"{BASE_URL}/api/whale-activities")
        assert response.status_code == 200
        data = response.json()
        
        assert "activities" in data
        # Activities may be empty if no whale activity detected yet
        print(f"✅ Whale activities passed: {len(data.get('activities', []))} activities")


class TestPriceAndTokens:
    """Price and token endpoint tests"""
    
    def test_sol_price_endpoint(self):
        """Test /api/sol-price returns SOL price"""
        response = requests.get(f"{BASE_URL}/api/sol-price")
        assert response.status_code == 200
        data = response.json()
        
        assert "price_usd" in data
        price = data.get("price_usd")
        assert price > 0  # SOL price should be positive
        
        print(f"✅ SOL price passed: ${price}")
    
    def test_trending_tokens_endpoint(self):
        """Test /api/trending-tokens returns trending tokens"""
        response = requests.get(f"{BASE_URL}/api/trending-tokens")
        assert response.status_code == 200
        data = response.json()
        
        assert "tokens" in data
        # Tokens list may vary based on market conditions
        print(f"✅ Trending tokens passed: {len(data.get('tokens', []))} tokens")


class TestPnLAndPositions:
    """P&L and positions endpoint tests"""
    
    def test_pnl_stats_endpoint(self):
        """Test /api/pnl-stats returns P&L statistics"""
        response = requests.get(f"{BASE_URL}/api/pnl-stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required P&L fields
        assert "total_pnl_usd" in data
        assert "total_trades" in data
        assert "winning_trades" in data
        assert "losing_trades" in data
        assert "win_rate" in data
        assert "active_positions" in data
        
        print(f"✅ P&L stats passed: total_pnl=${data.get('total_pnl_usd')}, win_rate={data.get('win_rate')}%")


class TestUserAndWalletEndpoints:
    """User and wallet endpoint tests"""
    
    def test_users_endpoint(self):
        """Test /api/users returns user list"""
        response = requests.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        data = response.json()
        
        assert "users" in data
        print(f"✅ Users endpoint passed: {len(data.get('users', []))} users")
    
    def test_trades_endpoint(self):
        """Test /api/trades returns trade list"""
        response = requests.get(f"{BASE_URL}/api/trades")
        assert response.status_code == 200
        data = response.json()
        
        assert "trades" in data
        print(f"✅ Trades endpoint passed: {len(data.get('trades', []))} trades")
    
    def test_payments_endpoint(self):
        """Test /api/payments returns payment list"""
        response = requests.get(f"{BASE_URL}/api/payments")
        assert response.status_code == 200
        data = response.json()
        
        assert "payments" in data
        print(f"✅ Payments endpoint passed: {len(data.get('payments', []))} payments")


class TestTelegramBot:
    """Telegram bot API tests"""
    
    def test_telegram_bot_getme(self):
        """Test Telegram bot responds to getMe API call"""
        bot_token = "8553687931:AAFZ87vcHiVsbrRRhcgX3fFe0D9zos-2JLM"
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe")
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("ok") == True
        result = data.get("result", {})
        assert result.get("is_bot") == True
        assert result.get("username") == "Cfsolanasoldier_bot"
        assert result.get("first_name") == "SOLANA SOLDIER MEV BOT"
        
        print(f"✅ Telegram bot getMe passed: @{result.get('username')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
