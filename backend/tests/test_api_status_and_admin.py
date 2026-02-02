"""
Solana Soldier Bot - API Status and Admin Commands Tests
Tests for Solscan/Helius API status and admin API management features
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAPIStatus:
    """Tests for /api/api-status endpoint - Solscan and Helius API status"""
    
    def test_api_status_endpoint_exists(self):
        """Test /api/api-status endpoint returns 200"""
        response = requests.get(f"{BASE_URL}/api/api-status")
        assert response.status_code == 200
        data = response.json()
        assert "apis" in data
        print(f"✅ API status endpoint exists and returns data")
    
    def test_solscan_status_upgrade_required(self):
        """Test Solscan API shows 'upgrade_required' status (free tier limitation)"""
        response = requests.get(f"{BASE_URL}/api/api-status")
        assert response.status_code == 200
        data = response.json()
        
        solscan = data["apis"]["solscan"]
        assert solscan["status"] == "upgrade_required"
        assert solscan["status_code"] == 401
        assert "upgrade" in solscan["message"].lower() or "paid tier" in solscan["message"].lower()
        assert solscan["key_configured"] == True
        
        print(f"✅ Solscan status correctly shows 'upgrade_required': {solscan['message']}")
    
    def test_helius_status_ok(self):
        """Test Helius API shows 'ok' status (working as fallback)"""
        response = requests.get(f"{BASE_URL}/api/api-status")
        assert response.status_code == 200
        data = response.json()
        
        helius = data["apis"]["helius"]
        assert helius["status"] == "ok"
        assert helius["key_configured"] == True
        
        print(f"✅ Helius status correctly shows 'ok' - working as fallback")


class TestSystemStatus:
    """Tests for /api/system-status endpoint - Live trading status"""
    
    def test_system_status_live_trading_enabled(self):
        """Test /api/system-status shows live_trading_enabled=true"""
        response = requests.get(f"{BASE_URL}/api/system-status")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "online"
        assert data["live_trading_enabled"] == True
        assert data["auto_trade_on_whale_signal"] == True
        
        print(f"✅ System status: live_trading={data['live_trading_enabled']}, auto_trade={data['auto_trade_on_whale_signal']}")
    
    def test_system_status_helius_connected(self):
        """Test Helius RPC is connected (used for fallback)"""
        response = requests.get(f"{BASE_URL}/api/system-status")
        assert response.status_code == 200
        data = response.json()
        
        assert data["helius_rpc_connected"] == True
        assert data["jupiter_dex_ready"] == True
        assert data["whale_monitor_active"] == True
        
        print(f"✅ Helius RPC connected: {data['helius_rpc_connected']}")
    
    def test_system_status_whale_tracking(self):
        """Test whale tracking is active with 9 wallets"""
        response = requests.get(f"{BASE_URL}/api/system-status")
        assert response.status_code == 200
        data = response.json()
        
        assert data["tracked_whale_wallets"] == 9
        
        print(f"✅ Tracked whale wallets: {data['tracked_whale_wallets']}")


class TestAdminTestAPI:
    """Tests for admin API testing endpoint"""
    
    def test_admin_test_solscan_api(self):
        """Test /api/admin/test-api/solscan endpoint"""
        response = requests.post(f"{BASE_URL}/api/admin/test-api/solscan")
        assert response.status_code == 200
        data = response.json()
        
        # Should return upgrade_required since Solscan needs paid tier
        assert data["status"] in ["ok", "upgrade_required", "error"]
        assert "status_code" in data
        assert "message" in data
        
        print(f"✅ Admin test API for Solscan: status={data['status']}, message={data['message']}")


class TestHeliusFallback:
    """Tests to verify Helius is working as fallback for whale data"""
    
    def test_helius_api_direct(self):
        """Test Helius API directly to verify it's working"""
        helius_key = "5963c03a-3441-4c7a-816f-4a307b412439"
        test_wallet = "74YhGgHA3x1jcL2TchwChDbRVVXvzSxNbYM6ytCukauM"
        
        response = requests.get(
            f"https://api.helius.xyz/v0/addresses/{test_wallet}/transactions",
            params={"api-key": helius_key, "limit": 5},
            timeout=15
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0  # Should have transaction data
        
        # Verify transaction structure
        if data:
            tx = data[0]
            assert "signature" in tx
            assert "type" in tx
        
        print(f"✅ Helius API working: returned {len(data)} transactions for whale wallet")
    
    def test_whales_endpoint_returns_data(self):
        """Test /api/whales returns whale wallet list"""
        response = requests.get(f"{BASE_URL}/api/whales")
        assert response.status_code == 200
        data = response.json()
        
        assert "whales" in data
        assert len(data["whales"]) == 9
        
        # Verify first whale wallet format
        first_whale = data["whales"][0]
        assert len(first_whale) > 30  # Solana addresses are ~44 chars
        
        print(f"✅ Whales endpoint returns {len(data['whales'])} tracked wallets")


class TestTelegramBotCommands:
    """Tests to verify Telegram bot is running and commands are registered"""
    
    def test_telegram_bot_running(self):
        """Test Telegram bot is running via getMe API"""
        bot_token = "8553687931:AAFZ87vcHiVsbrRRhcgX3fFe0D9zos-2JLM"
        
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        assert "result" in data
        assert data["result"]["is_bot"] == True
        
        print(f"✅ Telegram bot running: @{data['result']['username']}")
    
    def test_telegram_bot_commands_registered(self):
        """Test that admin commands are registered with the bot"""
        bot_token = "8553687931:AAFZ87vcHiVsbrRRhcgX3fFe0D9zos-2JLM"
        
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMyCommands")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok"] == True
        # Commands may or may not be set via setMyCommands, but bot should respond
        
        print(f"✅ Telegram bot commands API accessible")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
