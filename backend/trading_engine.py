"""
Solana Soldier Trading Engine v2
- Helius RPC Integration for fast blockchain queries
- Real-time WebSocket monitoring for whale wallets
- Live trade execution via Jupiter DEX
- Automated trading on whale signals
"""

import asyncio
import httpx
import base58
import logging
import json
import websockets
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.signature import Signature
import os

logger = logging.getLogger(__name__)

# Helius Configuration
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY', '')
HELIUS_RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
HELIUS_WS_URL = f"wss://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# Jupiter API
JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP_API = "https://quote-api.jup.ag/v6/swap"
JUPITER_PRICE_API = "https://price.jup.ag/v6/price"

# Solana Constants
WSOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
LAMPORTS_PER_SOL = 1_000_000_000

# Trading Parameters
MIN_PROFIT_USD = 2.0
MAX_TRADE_TIME_SECONDS = 120
MAX_SLIPPAGE_BPS = 150  # 1.5% slippage for live trades
MIN_LIQUIDITY_USD = 10000
GAS_RESERVE_SOL = 0.01  # Reserve for gas fees
MAX_TRADE_SOL = 0.5  # Maximum SOL per trade for safety

# Live trading flags
LIVE_TRADING_ENABLED = os.environ.get('LIVE_TRADING_ENABLED', 'false').lower() == 'true'
AUTO_TRADE_ON_WHALE_SIGNAL = os.environ.get('AUTO_TRADE_ON_WHALE_SIGNAL', 'false').lower() == 'true'


@dataclass
class TokenInfo:
    address: str
    symbol: str
    name: str
    decimals: int
    price_usd: float
    liquidity_usd: float
    market_cap: float
    holder_count: int
    created_at: Optional[datetime] = None
    creator_address: Optional[str] = None


@dataclass
class TradeSignal:
    token_address: str
    token_symbol: str
    action: str  # BUY or SELL
    reason: str
    confidence: float  # 0-1
    whale_address: Optional[str] = None
    estimated_profit_usd: float = 0.0
    risk_score: float = 0.0


@dataclass
class RugCheckResult:
    is_safe: bool
    risk_score: float
    warnings: List[str]
    details: Dict


@dataclass
class TradeResult:
    success: bool
    trade_id: str
    signature: Optional[str] = None
    action: str = ""
    token_address: str = ""
    token_symbol: str = ""
    amount_sol: float = 0.0
    amount_tokens: float = 0.0
    price_at_trade: float = 0.0
    error: Optional[str] = None


class HeliusRPC:
    """Helius RPC client for fast Solana blockchain queries"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or HELIUS_API_KEY
        self.rpc_url = f"https://mainnet.helius-rpc.com/?api-key={self.api_key}"
        self.client = httpx.AsyncClient(timeout=30)
    
    async def get_balance(self, address: str) -> float:
        """Get SOL balance for an address"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [address]
            }
            response = await self.client.post(self.rpc_url, json=payload)
            data = response.json()
            if "result" in data:
                return data["result"]["value"] / LAMPORTS_PER_SOL
            return 0.0
        except Exception as e:
            logger.error(f"Get balance error: {e}")
            return 0.0
    
    async def get_token_accounts(self, address: str) -> List[Dict]:
        """Get all token accounts for an address"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    address,
                    {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
                    {"encoding": "jsonParsed"}
                ]
            }
            response = await self.client.post(self.rpc_url, json=payload)
            data = response.json()
            if "result" in data:
                return data["result"]["value"]
            return []
        except Exception as e:
            logger.error(f"Get token accounts error: {e}")
            return []
    
    async def get_recent_transactions(self, address: str, limit: int = 10) -> List[Dict]:
        """Get recent transactions for an address"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [address, {"limit": limit}]
            }
            response = await self.client.post(self.rpc_url, json=payload)
            data = response.json()
            if "result" in data:
                return data["result"]
            return []
        except Exception as e:
            logger.error(f"Get transactions error: {e}")
            return []
    
    async def get_transaction(self, signature: str) -> Optional[Dict]:
        """Get transaction details"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTransaction",
                "params": [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
            }
            response = await self.client.post(self.rpc_url, json=payload)
            data = response.json()
            if "result" in data:
                return data["result"]
            return None
        except Exception as e:
            logger.error(f"Get transaction error: {e}")
            return None
    
    async def get_latest_blockhash(self) -> Optional[str]:
        """Get latest blockhash for transaction signing"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getLatestBlockhash",
                "params": [{"commitment": "finalized"}]
            }
            response = await self.client.post(self.rpc_url, json=payload)
            data = response.json()
            if "result" in data:
                return data["result"]["value"]["blockhash"]
            return None
        except Exception as e:
            logger.error(f"Get blockhash error: {e}")
            return None
    
    async def send_transaction(self, signed_tx: bytes) -> Tuple[bool, Optional[str], Optional[str]]:
        """Send a signed transaction"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sendTransaction",
                "params": [
                    base58.b58encode(signed_tx).decode('utf-8'),
                    {"encoding": "base58", "skipPreflight": False, "maxRetries": 3}
                ]
            }
            response = await self.client.post(self.rpc_url, json=payload)
            data = response.json()
            
            if "result" in data:
                return True, data["result"], None
            else:
                error = data.get("error", {}).get("message", "Unknown error")
                return False, None, error
        except Exception as e:
            logger.error(f"Send transaction error: {e}")
            return False, None, str(e)
    
    async def confirm_transaction(self, signature: str, timeout: int = 60) -> bool:
        """Wait for transaction confirmation"""
        try:
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < timeout:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getSignatureStatuses",
                    "params": [[signature]]
                }
                response = await self.client.post(self.rpc_url, json=payload)
                data = response.json()
                
                if "result" in data and data["result"]["value"][0]:
                    status = data["result"]["value"][0]
                    if status.get("confirmationStatus") in ["confirmed", "finalized"]:
                        return True
                    if status.get("err"):
                        logger.error(f"Transaction failed: {status['err']}")
                        return False
                
                await asyncio.sleep(2)
            return False
        except Exception as e:
            logger.error(f"Confirm transaction error: {e}")
            return False
    
    async def close(self):
        await self.client.aclose()


class HeliusWebSocket:
    """Real-time WebSocket monitoring using Helius Enhanced WebSockets"""
    
    def __init__(self, api_key: str = None, on_transaction: Callable = None):
        self.api_key = api_key or HELIUS_API_KEY
        self.ws_url = f"wss://mainnet.helius-rpc.com/?api-key={self.api_key}"
        self.on_transaction = on_transaction
        self.websocket = None
        self.is_running = False
        self.subscriptions = {}
        self.subscription_id = 0
    
    async def connect(self):
        """Establish WebSocket connection"""
        try:
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=30,
                ping_timeout=10
            )
            self.is_running = True
            logger.info("Helius WebSocket connected")
            return True
        except Exception as e:
            logger.error(f"WebSocket connect error: {e}")
            return False
    
    async def subscribe_to_account(self, address: str) -> Optional[int]:
        """Subscribe to account changes for a wallet"""
        if not self.websocket:
            return None
        
        try:
            self.subscription_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": self.subscription_id,
                "method": "accountSubscribe",
                "params": [
                    address,
                    {"encoding": "jsonParsed", "commitment": "confirmed"}
                ]
            }
            await self.websocket.send(json.dumps(request))
            
            # Wait for subscription confirmation
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            data = json.loads(response)
            
            if "result" in data:
                sub_id = data["result"]
                self.subscriptions[address] = sub_id
                logger.info(f"Subscribed to account {address[:8]}... (sub_id: {sub_id})")
                return sub_id
            return None
        except Exception as e:
            logger.error(f"Subscribe error: {e}")
            return None
    
    async def subscribe_to_logs(self, address: str) -> Optional[int]:
        """Subscribe to transaction logs mentioning an address"""
        if not self.websocket:
            return None
        
        try:
            self.subscription_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": self.subscription_id,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": [address]},
                    {"commitment": "confirmed"}
                ]
            }
            await self.websocket.send(json.dumps(request))
            
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            data = json.loads(response)
            
            if "result" in data:
                sub_id = data["result"]
                logger.info(f"Subscribed to logs for {address[:8]}... (sub_id: {sub_id})")
                return sub_id
            return None
        except Exception as e:
            logger.error(f"Subscribe logs error: {e}")
            return None
    
    async def listen(self):
        """Listen for incoming WebSocket messages"""
        if not self.websocket:
            return
        
        while self.is_running:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=60)
                data = json.loads(message)
                
                if "method" in data and data["method"] == "accountNotification":
                    await self._handle_account_notification(data)
                elif "method" in data and data["method"] == "logsNotification":
                    await self._handle_logs_notification(data)
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    pong = await self.websocket.ping()
                    await asyncio.wait_for(pong, timeout=10)
                except:
                    logger.warning("WebSocket ping failed, reconnecting...")
                    await self._reconnect()
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
                await self._reconnect()
            except Exception as e:
                logger.error(f"WebSocket listen error: {e}")
                await asyncio.sleep(5)
    
    async def _handle_account_notification(self, data: Dict):
        """Handle account change notification"""
        try:
            params = data.get("params", {})
            result = params.get("result", {})
            
            if self.on_transaction:
                await self.on_transaction({
                    "type": "account_change",
                    "data": result
                })
        except Exception as e:
            logger.error(f"Handle account notification error: {e}")
    
    async def _handle_logs_notification(self, data: Dict):
        """Handle transaction logs notification"""
        try:
            params = data.get("params", {})
            result = params.get("result", {})
            value = result.get("value", {})
            
            signature = value.get("signature")
            logs = value.get("logs", [])
            
            if self.on_transaction:
                await self.on_transaction({
                    "type": "transaction",
                    "signature": signature,
                    "logs": logs
                })
        except Exception as e:
            logger.error(f"Handle logs notification error: {e}")
    
    async def _reconnect(self):
        """Reconnect WebSocket and resubscribe"""
        try:
            if self.websocket:
                await self.websocket.close()
            
            await asyncio.sleep(5)
            await self.connect()
            
            # Resubscribe to all addresses
            old_subscriptions = list(self.subscriptions.keys())
            self.subscriptions.clear()
            
            for address in old_subscriptions:
                await self.subscribe_to_logs(address)
                
        except Exception as e:
            logger.error(f"Reconnect error: {e}")
    
    async def close(self):
        """Close WebSocket connection"""
        self.is_running = False
        if self.websocket:
            await self.websocket.close()


class JupiterDEX:
    """Jupiter DEX integration for live Solana swaps"""
    
    def __init__(self, helius_rpc: HeliusRPC = None):
        self.client = httpx.AsyncClient(timeout=30)
        self.helius = helius_rpc or HeliusRPC()
    
    async def get_quote(
        self, 
        input_mint: str, 
        output_mint: str, 
        amount: int,
        slippage_bps: int = MAX_SLIPPAGE_BPS
    ) -> Optional[Dict]:
        """Get swap quote from Jupiter"""
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": amount,
                "slippageBps": slippage_bps,
                "onlyDirectRoutes": False,
                "asLegacyTransaction": False
            }
            response = await self.client.get(JUPITER_QUOTE_API, params=params)
            if response.status_code == 200:
                return response.json()
            logger.error(f"Jupiter quote error: {response.status_code} - {response.text}")
            return None
        except Exception as e:
            logger.error(f"Jupiter quote exception: {e}")
            return None
    
    async def get_swap_transaction(
        self,
        quote_response: Dict,
        user_public_key: str,
        wrap_unwrap_sol: bool = True
    ) -> Optional[bytes]:
        """Get serialized swap transaction"""
        try:
            payload = {
                "quoteResponse": quote_response,
                "userPublicKey": user_public_key,
                "wrapAndUnwrapSol": wrap_unwrap_sol,
                "dynamicComputeUnitLimit": True,
                "prioritizationFeeLamports": "auto"
            }
            response = await self.client.post(JUPITER_SWAP_API, json=payload)
            if response.status_code == 200:
                data = response.json()
                return base58.b58decode(data["swapTransaction"])
            logger.error(f"Jupiter swap error: {response.status_code} - {response.text}")
            return None
        except Exception as e:
            logger.error(f"Jupiter swap exception: {e}")
            return None
    
    async def execute_swap(
        self,
        keypair: Keypair,
        input_mint: str,
        output_mint: str,
        amount_lamports: int,
        slippage_bps: int = MAX_SLIPPAGE_BPS
    ) -> TradeResult:
        """Execute a live swap on Jupiter"""
        import uuid
        trade_id = str(uuid.uuid4())
        
        try:
            logger.info(f"[LIVE TRADE] Starting swap: {amount_lamports/LAMPORTS_PER_SOL:.4f} SOL -> {output_mint[:8]}...")
            
            # Step 1: Get quote
            quote = await self.get_quote(input_mint, output_mint, amount_lamports, slippage_bps)
            if not quote:
                return TradeResult(
                    success=False,
                    trade_id=trade_id,
                    error="Failed to get quote"
                )
            
            out_amount = int(quote.get("outAmount", 0))
            price_impact = float(quote.get("priceImpactPct", 0))
            
            logger.info(f"[LIVE TRADE] Quote received: out={out_amount}, price_impact={price_impact}%")
            
            # Safety check: reject high price impact
            if price_impact > 5:
                return TradeResult(
                    success=False,
                    trade_id=trade_id,
                    error=f"Price impact too high: {price_impact}%"
                )
            
            # Step 2: Get swap transaction
            swap_tx_bytes = await self.get_swap_transaction(
                quote, 
                str(keypair.pubkey())
            )
            if not swap_tx_bytes:
                return TradeResult(
                    success=False,
                    trade_id=trade_id,
                    error="Failed to get swap transaction"
                )
            
            # Step 3: Sign transaction
            tx = VersionedTransaction.from_bytes(swap_tx_bytes)
            tx.sign([keypair])
            signed_tx = bytes(tx)
            
            logger.info(f"[LIVE TRADE] Transaction signed, sending...")
            
            # Step 4: Send transaction via Helius RPC
            success, signature, error = await self.helius.send_transaction(signed_tx)
            
            if not success:
                return TradeResult(
                    success=False,
                    trade_id=trade_id,
                    error=error
                )
            
            logger.info(f"[LIVE TRADE] Transaction sent: {signature}")
            
            # Step 5: Confirm transaction
            confirmed = await self.helius.confirm_transaction(signature, timeout=60)
            
            if confirmed:
                logger.info(f"[LIVE TRADE] ✅ Transaction confirmed: {signature}")
                return TradeResult(
                    success=True,
                    trade_id=trade_id,
                    signature=signature,
                    action="BUY" if input_mint == WSOL_MINT else "SELL",
                    token_address=output_mint if input_mint == WSOL_MINT else input_mint,
                    amount_sol=amount_lamports / LAMPORTS_PER_SOL,
                    amount_tokens=out_amount
                )
            else:
                return TradeResult(
                    success=False,
                    trade_id=trade_id,
                    signature=signature,
                    error="Transaction not confirmed within timeout"
                )
                    
        except Exception as e:
            logger.error(f"[LIVE TRADE] Swap execution error: {e}")
            return TradeResult(
                success=False,
                trade_id=trade_id,
                error=str(e)
            )
    
    async def get_token_price(self, token_mint: str) -> Optional[float]:
        """Get token price in USD"""
        try:
            params = {"ids": token_mint}
            response = await self.client.get(JUPITER_PRICE_API, params=params)
            if response.status_code == 200:
                data = response.json()
                if "data" in data and token_mint in data["data"]:
                    return data["data"][token_mint].get("price", 0)
            return None
        except Exception as e:
            logger.error(f"Price fetch error: {e}")
            return None
    
    async def close(self):
        await self.client.aclose()
        if self.helius:
            await self.helius.close()


class RugDetector:
    """Rug pull detection algorithm using Helius RPC"""
    
    RUG_INDICATORS = {
        "low_liquidity": 5000,
        "high_creator_holdings": 0.5,
        "low_holder_count": 50,
        "new_token_hours": 24,
        "high_tax": 0.1,
    }
    
    def __init__(self, solscan_api_key: str = None, helius_rpc: HeliusRPC = None):
        self.solscan_api_key = solscan_api_key
        self.helius = helius_rpc or HeliusRPC()
        self.client = httpx.AsyncClient(timeout=30)
    
    async def check_token(self, token_address: str) -> RugCheckResult:
        """Comprehensive rug check for a token"""
        warnings = []
        risk_factors = []
        details = {}
        
        try:
            # Fetch token metadata
            token_info = await self._get_token_info(token_address)
            details["token_info"] = token_info
            
            # Check 1: Liquidity
            liquidity = token_info.get("liquidity_usd", 0)
            if liquidity < self.RUG_INDICATORS["low_liquidity"]:
                warnings.append(f"Low liquidity: ${liquidity:.2f}")
                risk_factors.append(0.3)
            details["liquidity_usd"] = liquidity
            
            # Check 2: Holder count
            holder_count = token_info.get("holder_count", 0)
            if holder_count < self.RUG_INDICATORS["low_holder_count"]:
                warnings.append(f"Low holder count: {holder_count}")
                risk_factors.append(0.2)
            details["holder_count"] = holder_count
            
            # Check 3: Token age
            created_at = token_info.get("created_at")
            if created_at:
                age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
                if age_hours < self.RUG_INDICATORS["new_token_hours"]:
                    warnings.append(f"New token: {age_hours:.1f} hours old")
                    risk_factors.append(0.15)
                details["age_hours"] = age_hours
            
            # Check 4: Mint/Freeze authority via Helius
            authorities = await self._check_authorities_helius(token_address)
            if authorities.get("mint_authority"):
                warnings.append("Mint authority enabled - can create more tokens")
                risk_factors.append(0.25)
            if authorities.get("freeze_authority"):
                warnings.append("Freeze authority enabled - can freeze tokens")
                risk_factors.append(0.2)
            details["authorities"] = authorities
            
            # Check 5: Known rugger
            is_known_rugger = await self._check_known_ruggers(token_info.get("creator"))
            if is_known_rugger:
                warnings.append("Creator is a known rugger!")
                risk_factors.append(0.5)
            details["known_rugger"] = is_known_rugger
            
            risk_score = min(1.0, sum(risk_factors))
            is_safe = risk_score < 0.5
            
            return RugCheckResult(
                is_safe=is_safe,
                risk_score=risk_score,
                warnings=warnings,
                details=details
            )
            
        except Exception as e:
            logger.error(f"Rug check error: {e}")
            return RugCheckResult(
                is_safe=False,
                risk_score=1.0,
                warnings=["Failed to perform rug check"],
                details={"error": str(e)}
            )
    
    async def _get_token_info(self, token_address: str) -> Dict:
        """Fetch token information from DexScreener"""
        try:
            response = await self.client.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            )
            if response.status_code == 200:
                data = response.json()
                pairs = data.get("pairs", [])
                if pairs:
                    p = pairs[0]
                    return {
                        "symbol": p.get("baseToken", {}).get("symbol"),
                        "name": p.get("baseToken", {}).get("name"),
                        "liquidity_usd": float(p.get("liquidity", {}).get("usd", 0) or 0),
                        "holder_count": 100,  # DexScreener doesn't provide this
                        "price_usd": float(p.get("priceUsd", 0) or 0),
                    }
            return {}
        except Exception as e:
            logger.error(f"Token info error: {e}")
            return {}
    
    async def _check_authorities_helius(self, token_address: str) -> Dict:
        """Check mint/freeze authorities using Helius RPC"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAccountInfo",
                "params": [token_address, {"encoding": "jsonParsed"}]
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(self.helius.rpc_url, json=payload)
                data = response.json()
                
                if "result" in data and data["result"]["value"]:
                    parsed = data["result"]["value"]["data"]["parsed"]["info"]
                    return {
                        "mint_authority": parsed.get("mintAuthority") is not None,
                        "freeze_authority": parsed.get("freezeAuthority") is not None
                    }
            return {"mint_authority": False, "freeze_authority": False}
        except Exception as e:
            logger.error(f"Authority check error: {e}")
            return {"mint_authority": True, "freeze_authority": True}
    
    async def _check_known_ruggers(self, creator_address: Optional[str]) -> bool:
        """Check if creator is in known rugger database"""
        if not creator_address:
            return False
        
        KNOWN_RUGGERS = [
            "AUFxnVLsKkkupjCY4kmA5ZDH8c4HgK7CZ4FYw1VcXpn8",
        ]
        return creator_address in KNOWN_RUGGERS
    
    async def close(self):
        await self.client.aclose()


class WhaleMonitorWebSocket:
    """Real-time whale monitoring using Helius WebSocket"""
    
    def __init__(
        self,
        whale_wallets: List[str],
        helius_api_key: str,
        on_whale_activity: Callable = None,
        helius_rpc: HeliusRPC = None
    ):
        self.whale_wallets = whale_wallets
        self.helius_api_key = helius_api_key
        self.on_whale_activity = on_whale_activity
        self.helius_rpc = helius_rpc or HeliusRPC(helius_api_key)
        self.helius_ws = None
        self.is_running = False
        self.last_signatures: Dict[str, str] = {}
    
    async def start(self):
        """Start WebSocket monitoring"""
        self.is_running = True
        
        # Create WebSocket connection
        self.helius_ws = HeliusWebSocket(
            api_key=self.helius_api_key,
            on_transaction=self._handle_transaction
        )
        
        connected = await self.helius_ws.connect()
        if not connected:
            logger.error("Failed to connect WebSocket, falling back to polling")
            asyncio.create_task(self._fallback_polling())
            return
        
        # Subscribe to whale wallets
        for wallet in self.whale_wallets:
            await self.helius_ws.subscribe_to_logs(wallet)
            await asyncio.sleep(0.5)  # Rate limit
        
        # Start listening
        asyncio.create_task(self.helius_ws.listen())
        logger.info(f"WebSocket monitoring started for {len(self.whale_wallets)} whales")
    
    async def _handle_transaction(self, event: Dict):
        """Handle incoming transaction event"""
        try:
            if event.get("type") == "transaction":
                signature = event.get("signature")
                logs = event.get("logs", [])
                
                # Check if it's a token transfer/swap
                is_token_activity = any(
                    "Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA" in log or
                    "Transfer" in log or
                    "Swap" in log
                    for log in logs
                )
                
                if is_token_activity and signature:
                    # Get full transaction details
                    tx_details = await self.helius_rpc.get_transaction(signature)
                    if tx_details:
                        activity = await self._parse_transaction(signature, tx_details)
                        if activity and self.on_whale_activity:
                            await self.on_whale_activity(activity)
                            
        except Exception as e:
            logger.error(f"Handle transaction error: {e}")
    
    async def _parse_transaction(self, signature: str, tx_details: Dict) -> Optional[Dict]:
        """Parse transaction to extract whale activity"""
        try:
            meta = tx_details.get("meta", {})
            transaction = tx_details.get("transaction", {})
            
            # Get pre/post token balances
            pre_balances = meta.get("preTokenBalances", [])
            post_balances = meta.get("postTokenBalances", [])
            
            # Find token changes
            for post in post_balances:
                owner = post.get("owner")
                if owner in self.whale_wallets:
                    mint = post.get("mint")
                    post_amount = float(post.get("uiTokenAmount", {}).get("uiAmount", 0) or 0)
                    
                    # Find pre-balance
                    pre_amount = 0
                    for pre in pre_balances:
                        if pre.get("owner") == owner and pre.get("mint") == mint:
                            pre_amount = float(pre.get("uiTokenAmount", {}).get("uiAmount", 0) or 0)
                            break
                    
                    change = post_amount - pre_amount
                    if abs(change) > 0.001:  # Significant change
                        return {
                            "whale_address": owner,
                            "signature": signature,
                            "token_address": mint,
                            "token_symbol": "TOKEN",
                            "amount": abs(change),
                            "action": "BUY" if change > 0 else "SELL",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
            
            return None
        except Exception as e:
            logger.error(f"Parse transaction error: {e}")
            return None
    
    async def _fallback_polling(self):
        """Fallback to polling if WebSocket fails"""
        logger.info("Starting fallback polling for whale wallets")
        
        while self.is_running:
            try:
                for wallet in self.whale_wallets:
                    txs = await self.helius_rpc.get_recent_transactions(wallet, limit=5)
                    
                    for tx in txs:
                        sig = tx.get("signature")
                        if wallet in self.last_signatures and sig == self.last_signatures[wallet]:
                            break
                        
                        if sig:
                            tx_details = await self.helius_rpc.get_transaction(sig)
                            if tx_details:
                                activity = await self._parse_transaction(sig, tx_details)
                                if activity and self.on_whale_activity:
                                    await self.on_whale_activity(activity)
                    
                    if txs:
                        self.last_signatures[wallet] = txs[0].get("signature")
                    
                    await asyncio.sleep(1)  # Rate limit between wallets
                
                await asyncio.sleep(10)  # Poll interval
                
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Stop monitoring"""
        self.is_running = False
        if self.helius_ws:
            await self.helius_ws.close()
    
    async def close(self):
        await self.stop()
        if self.helius_rpc:
            await self.helius_rpc.close()


class LiveAutoTrader:
    """Automated live trading on whale signals"""
    
    def __init__(
        self,
        jupiter: JupiterDEX,
        rug_detector: RugDetector,
        helius_rpc: HeliusRPC,
        db,
        telegram_notify: Callable = None,
        min_profit_usd: float = MIN_PROFIT_USD,
        max_trade_sol: float = MAX_TRADE_SOL
    ):
        self.jupiter = jupiter
        self.rug_detector = rug_detector
        self.helius = helius_rpc
        self.db = db
        self.telegram_notify = telegram_notify
        self.min_profit_usd = min_profit_usd
        self.max_trade_sol = max_trade_sol
        self.active_positions: Dict[str, Dict] = {}
        self.is_enabled = LIVE_TRADING_ENABLED and AUTO_TRADE_ON_WHALE_SIGNAL
    
    async def process_whale_signal(
        self,
        activity: Dict,
        user_keypair: Keypair,
        user_telegram_id: int,
        trade_amount_sol: float
    ) -> Optional[TradeResult]:
        """
        Process whale activity and execute trade if conditions met
        """
        if not self.is_enabled:
            logger.info("Live trading disabled, skipping whale signal")
            return None
        
        token_address = activity.get("token_address")
        whale_action = activity.get("action")
        
        # Only follow whale buys
        if whale_action != "BUY":
            logger.info(f"Ignoring whale {whale_action} action")
            return None
        
        # Skip WSOL/USDC
        if token_address in [WSOL_MINT, USDC_MINT]:
            return None
        
        logger.info(f"[AUTO-TRADE] Processing whale signal for {token_address[:8]}...")
        
        # Step 1: Rug check
        rug_result = await self.rug_detector.check_token(token_address)
        if not rug_result.is_safe:
            logger.warning(f"[AUTO-TRADE] Token failed rug check: {rug_result.warnings}")
            if self.telegram_notify:
                await self.telegram_notify(
                    user_telegram_id,
                    f"⚠️ Skipped trade - Rug risk detected:\n{', '.join(rug_result.warnings[:2])}"
                )
            return None
        
        # Step 2: Check liquidity
        liquidity = rug_result.details.get("liquidity_usd", 0)
        if liquidity < MIN_LIQUIDITY_USD:
            logger.warning(f"[AUTO-TRADE] Low liquidity: ${liquidity}")
            return None
        
        # Step 3: Check wallet balance
        user_balance = await self.helius.get_balance(str(user_keypair.pubkey()))
        if user_balance < trade_amount_sol + GAS_RESERVE_SOL:
            logger.warning(f"[AUTO-TRADE] Insufficient balance: {user_balance} SOL")
            if self.telegram_notify:
                await self.telegram_notify(
                    user_telegram_id,
                    f"❌ Trade skipped - Insufficient balance\nRequired: {trade_amount_sol + GAS_RESERVE_SOL:.4f} SOL\nAvailable: {user_balance:.4f} SOL"
                )
            return None
        
        # Step 4: Enforce max trade limit
        actual_trade_amount = min(trade_amount_sol, self.max_trade_sol)
        amount_lamports = int(actual_trade_amount * LAMPORTS_PER_SOL)
        
        # Step 5: Notify user trade is starting
        if self.telegram_notify:
            await self.telegram_notify(
                user_telegram_id,
                f"🚀 *EXECUTING TRADE*\n\nWhale detected buying!\nToken: `{token_address[:16]}...`\nAmount: {actual_trade_amount:.4f} SOL\n\nProcessing..."
            )
        
        # Step 6: Execute trade
        result = await self.jupiter.execute_swap(
            keypair=user_keypair,
            input_mint=WSOL_MINT,
            output_mint=token_address,
            amount_lamports=amount_lamports,
            slippage_bps=MAX_SLIPPAGE_BPS
        )
        
        # Step 7: Record trade and notify
        if result.success:
            # Store position for exit monitoring
            self.active_positions[token_address] = {
                "trade_id": result.trade_id,
                "user_telegram_id": user_telegram_id,
                "keypair": user_keypair,
                "entry_time": datetime.now(timezone.utc),
                "amount_sol": actual_trade_amount,
                "amount_tokens": result.amount_tokens,
                "token_address": token_address
            }
            
            # Start exit monitor
            asyncio.create_task(self._monitor_for_exit(token_address))
            
            if self.telegram_notify:
                await self.telegram_notify(
                    user_telegram_id,
                    f"✅ *TRADE EXECUTED*\n\nSignature: `{result.signature[:20]}...`\nToken: `{token_address[:16]}...`\nAmount: {actual_trade_amount:.4f} SOL\n\n[View on Solscan](https://solscan.io/tx/{result.signature})"
                )
            
            logger.info(f"[AUTO-TRADE] ✅ Trade successful: {result.signature}")
        else:
            if self.telegram_notify:
                await self.telegram_notify(
                    user_telegram_id,
                    f"❌ *TRADE FAILED*\n\nError: {result.error}\n\nPlease check your wallet balance and try again."
                )
            logger.error(f"[AUTO-TRADE] ❌ Trade failed: {result.error}")
        
        return result
    
    async def _monitor_for_exit(self, token_address: str):
        """Monitor position and exit when profit target reached"""
        position = self.active_positions.get(token_address)
        if not position:
            return
        
        entry_time = position["entry_time"]
        user_telegram_id = position["user_telegram_id"]
        keypair = position["keypair"]
        amount_tokens = position["amount_tokens"]
        
        logger.info(f"[AUTO-TRADE] Monitoring position for exit: {token_address[:8]}...")
        
        while token_address in self.active_positions:
            try:
                elapsed = (datetime.now(timezone.utc) - entry_time).total_seconds()
                
                # Check timeout
                if elapsed > MAX_TRADE_TIME_SECONDS:
                    logger.info(f"[AUTO-TRADE] Position timeout, executing exit")
                    await self._execute_exit(token_address, "TIMEOUT")
                    break
                
                # Check profit (simplified - get current price)
                current_price = await self.jupiter.get_token_price(token_address)
                if current_price:
                    # Calculate unrealized P&L
                    current_value_usd = amount_tokens * current_price
                    entry_sol = position["amount_sol"]
                    sol_price = await self.jupiter.get_token_price(WSOL_MINT)
                    entry_value_usd = entry_sol * (sol_price or 200)
                    
                    profit_usd = current_value_usd - entry_value_usd
                    
                    if profit_usd >= self.min_profit_usd:
                        logger.info(f"[AUTO-TRADE] Profit target reached: ${profit_usd:.2f}")
                        await self._execute_exit(token_address, f"PROFIT_TARGET (${profit_usd:.2f})")
                        break
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"[AUTO-TRADE] Monitor error: {e}")
                await asyncio.sleep(5)
    
    async def _execute_exit(self, token_address: str, reason: str):
        """Exit position by selling tokens"""
        position = self.active_positions.pop(token_address, None)
        if not position:
            return
        
        user_telegram_id = position["user_telegram_id"]
        keypair = position["keypair"]
        amount_tokens = int(position["amount_tokens"])
        
        if amount_tokens <= 0:
            return
        
        logger.info(f"[AUTO-TRADE] Executing exit: {token_address[:8]}... reason: {reason}")
        
        # Sell tokens back to SOL
        result = await self.jupiter.execute_swap(
            keypair=keypair,
            input_mint=token_address,
            output_mint=WSOL_MINT,
            amount_lamports=amount_tokens,
            slippage_bps=MAX_SLIPPAGE_BPS
        )
        
        if result.success:
            if self.telegram_notify:
                await self.telegram_notify(
                    user_telegram_id,
                    f"💰 *POSITION CLOSED*\n\nReason: {reason}\nSignature: `{result.signature[:20]}...`\n\n[View on Solscan](https://solscan.io/tx/{result.signature})"
                )
            logger.info(f"[AUTO-TRADE] ✅ Exit successful: {result.signature}")
        else:
            if self.telegram_notify:
                await self.telegram_notify(
                    user_telegram_id,
                    f"⚠️ *EXIT FAILED*\n\nReason: {result.error}\n\nManual exit may be required."
                )
            logger.error(f"[AUTO-TRADE] ❌ Exit failed: {result.error}")
    
    async def get_active_positions(self) -> List[Dict]:
        """Get all active positions"""
        return [
            {
                "token_address": addr,
                "entry_time": pos["entry_time"].isoformat(),
                "amount_sol": pos["amount_sol"],
                "user_telegram_id": pos["user_telegram_id"]
            }
            for addr, pos in self.active_positions.items()
        ]


class TrendingTokenScanner:
    """Scan for trending tokens on DEXes"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30)
    
    async def get_trending_tokens(self) -> List[Dict]:
        """Get trending Solana tokens"""
        try:
            tokens = []
            
            # Fetch from pairs endpoint
            response = await self.client.get(
                "https://api.dexscreener.com/latest/dex/pairs/solana"
            )
            if response.status_code == 200:
                data = response.json()
                pairs = data.get("pairs", [])[:20]
                for p in pairs:
                    tokens.append({
                        "address": p.get("baseToken", {}).get("address"),
                        "symbol": p.get("baseToken", {}).get("symbol"),
                        "name": p.get("baseToken", {}).get("name"),
                        "price_usd": float(p.get("priceUsd", 0) or 0),
                        "liquidity_usd": float(p.get("liquidity", {}).get("usd", 0) or 0),
                        "volume_24h": float(p.get("volume", {}).get("h24", 0) or 0),
                        "price_change_24h": float(p.get("priceChange", {}).get("h24", 0) or 0),
                        "dex": p.get("dexId")
                    })
            
            # Remove duplicates
            seen = set()
            unique = []
            for t in tokens:
                if t["address"] and t["address"] not in seen:
                    seen.add(t["address"])
                    unique.append(t)
            
            return sorted(unique, key=lambda x: x.get("volume_24h", 0), reverse=True)[:20]
        except Exception as e:
            logger.error(f"Trending tokens error: {e}")
            return []
    
    async def close(self):
        await self.client.aclose()
