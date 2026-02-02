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


class TestLeaderboard:
    """Leaderboard endpoint tests - NEW FEATURE"""
    
    def test_leaderboard_endpoint(self):
        """Test /api/leaderboard returns leaderboard data"""
        response = requests.get(f"{BASE_URL}/api/leaderboard")
        assert response.status_code == 200
        data = response.json()
        
        assert "leaderboard" in data
        leaderboard = data.get("leaderboard", [])
        
        # Leaderboard may be empty if no trades yet
        if leaderboard:
            # Verify structure of leaderboard entries
            for entry in leaderboard:
                assert "telegram_id" in entry
                assert "username" in entry
                assert "total_profit" in entry
                assert "total_trades" in entry
                assert "successful_trades" in entry
                assert "win_rate" in entry
        
        print(f"✅ Leaderboard endpoint passed: {len(leaderboard)} traders on leaderboard")


class TestAdminDashboard:
    """Admin dashboard endpoint tests - NEW FEATURE"""
    
    def test_admin_dashboard_endpoint(self):
        """Test /api/admin/dashboard returns admin stats"""
        response = requests.get(f"{BASE_URL}/api/admin/dashboard")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required admin dashboard fields
        assert "total_users" in data
        assert "total_wallets" in data
        assert "total_trades" in data
        assert "total_profit_usd" in data
        assert "pending_payments" in data
        assert "active_traders" in data
        assert "successful_trades" in data
        assert "win_rate" in data
        assert "today_trades" in data
        assert "today_signups" in data
        assert "live_trading_enabled" in data
        assert "auto_trade_enabled" in data
        assert "tracked_whales" in data
        
        # Verify live trading is enabled
        assert data.get("live_trading_enabled") == True
        assert data.get("auto_trade_enabled") == True
        assert data.get("tracked_whales") == 9
        
        print(f"✅ Admin dashboard passed: users={data.get('total_users')}, trades={data.get('total_trades')}, profit=${data.get('total_profit_usd')}")


class TestFaucetMining:
    """Faucet mining endpoint tests - NEW FEATURE (Solana Soldiers)"""
    
    def test_faucets_endpoint(self):
        """Test /api/faucets returns 48+ faucets"""
        response = requests.get(f"{BASE_URL}/api/faucets")
        assert response.status_code == 200
        data = response.json()
        
        assert "faucets" in data
        assert "stats" in data
        
        faucets = data.get("faucets", [])
        stats = data.get("stats", {})
        
        # Verify we have 48+ faucets as specified
        assert len(faucets) >= 48, f"Expected 48+ faucets, got {len(faucets)}"
        
        # Verify faucet structure
        if faucets:
            faucet = faucets[0]
            assert "name" in faucet
            assert "url" in faucet
            assert "chain" in faucet
            assert "currency" in faucet
            assert "amount_range" in faucet
            assert "cooldown_hours" in faucet
        
        # Verify stats structure
        assert "total_faucets" in stats
        assert "mainnet_faucets" in stats
        assert "testnet_faucets" in stats
        assert stats.get("total_faucets") >= 48
        
        print(f"✅ Faucets endpoint passed: {len(faucets)} faucets available, mainnet={stats.get('mainnet_faucets')}, testnet={stats.get('testnet_faucets')}")
    
    def test_mining_sessions_endpoint(self):
        """Test /api/mining-sessions returns mining session list"""
        response = requests.get(f"{BASE_URL}/api/mining-sessions")
        assert response.status_code == 200
        data = response.json()
        
        assert "sessions" in data
        print(f"✅ Mining sessions endpoint passed: {len(data.get('sessions', []))} sessions")


class TestNFTAggregator:
    """NFT aggregator endpoint tests - NEW FEATURE"""
    
    def test_nft_trending_solana(self):
        """Test /api/nft/trending/solana returns NFT collections"""
        response = requests.get(f"{BASE_URL}/api/nft/trending/solana")
        assert response.status_code == 200
        data = response.json()
        
        assert "collections" in data
        collections = data.get("collections", [])
        
        # Collections may be empty if API calls fail
        if collections:
            # Verify collection structure
            collection = collections[0]
            assert "name" in collection
            assert "symbol" in collection
            assert "marketplace" in collection
            assert "chain" in collection
            assert "floor_price" in collection
            assert "currency" in collection
            assert "volume_24h" in collection
            assert "listed_count" in collection
            assert "verified" in collection
            
            # Verify chain is solana
            assert collection.get("chain") == "solana"
        
        print(f"✅ NFT trending Solana passed: {len(collections)} collections")
    
    def test_nft_trending_ethereum(self):
        """Test /api/nft/trending/ethereum returns NFT collections"""
        response = requests.get(f"{BASE_URL}/api/nft/trending/ethereum")
        assert response.status_code == 200
        data = response.json()
        
        assert "collections" in data
        collections = data.get("collections", [])
        
        # Collections may be empty if API calls fail
        if collections:
            # Verify chain is ethereum
            collection = collections[0]
            assert collection.get("chain") == "ethereum"
        
        print(f"✅ NFT trending Ethereum passed: {len(collections)} collections")


class TestQuickTradeAmounts:
    """Quick trade amount configuration tests - NEW FEATURE"""
    
    def test_system_status_trade_amounts(self):
        """Test /api/system-status shows trade amount configuration"""
        response = requests.get(f"{BASE_URL}/api/system-status")
        assert response.status_code == 200
        data = response.json()
        
        # Verify trade amount bounds
        min_trade = data.get("min_trade_sol")
        max_trade = data.get("max_trade_sol")
        
        assert min_trade is not None
        assert max_trade is not None
        assert min_trade > 0
        assert max_trade > min_trade
        
        # Quick trade supports $2-$500 per trade
        # At ~$200 SOL price, $2 = 0.01 SOL, $500 = 2.5 SOL
        # Current config: min=0.02, max=0.5 SOL
        print(f"✅ Trade amounts passed: min={min_trade} SOL, max={max_trade} SOL")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
