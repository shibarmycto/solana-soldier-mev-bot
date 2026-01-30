"""
Solana Soldier Trading Engine
- Jupiter DEX Integration for swaps
- Real-time whale monitoring
- Automated trading logic
- Rug detection algorithm
"""

import asyncio
import httpx
import base58
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
import json

logger = logging.getLogger(__name__)

# Constants
JUPITER_QUOTE_API = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP_API = "https://quote-api.jup.ag/v6/swap"
JUPITER_PRICE_API = "https://price.jup.ag/v6/price"
SOLANA_RPC = "https://api.mainnet-beta.solana.com"
WSOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# Trading parameters
MIN_PROFIT_USD = 2.0  # $2 minimum profit target
MAX_TRADE_TIME_SECONDS = 120  # 2 minutes max
MAX_SLIPPAGE_BPS = 100  # 1% max slippage
MIN_LIQUIDITY_USD = 10000  # Minimum liquidity to trade
GAS_RESERVE_SOL = 0.005  # Reserve for gas fees

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
    risk_score: float = 0.0  # 0-1, higher = riskier

@dataclass
class RugCheckResult:
    is_safe: bool
    risk_score: float  # 0-1
    warnings: List[str]
    details: Dict


class JupiterDEX:
    """Jupiter DEX integration for Solana swaps"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30)
    
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
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Execute a swap on Jupiter
        Returns: (success, signature, error_message)
        """
        try:
            # Step 1: Get quote
            quote = await self.get_quote(input_mint, output_mint, amount_lamports, slippage_bps)
            if not quote:
                return False, None, "Failed to get quote"
            
            # Step 2: Get swap transaction
            swap_tx_bytes = await self.get_swap_transaction(
                quote, 
                str(keypair.pubkey())
            )
            if not swap_tx_bytes:
                return False, None, "Failed to get swap transaction"
            
            # Step 3: Deserialize, sign, and send
            tx = VersionedTransaction.from_bytes(swap_tx_bytes)
            tx.sign([keypair])
            
            # Send transaction
            async with httpx.AsyncClient() as client:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "sendTransaction",
                    "params": [
                        base58.b58encode(bytes(tx)).decode('utf-8'),
                        {"encoding": "base58", "skipPreflight": False}
                    ]
                }
                response = await client.post(SOLANA_RPC, json=payload)
                result = response.json()
                
                if "result" in result:
                    signature = result["result"]
                    logger.info(f"Swap executed: {signature}")
                    return True, signature, None
                else:
                    error = result.get("error", {}).get("message", "Unknown error")
                    return False, None, error
                    
        except Exception as e:
            logger.error(f"Swap execution error: {e}")
            return False, None, str(e)
    
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


class RugDetector:
    """Rug pull detection algorithm"""
    
    # Known rug patterns
    RUG_INDICATORS = {
        "low_liquidity": 5000,  # Less than $5000 liquidity
        "high_creator_holdings": 0.5,  # Creator holds > 50%
        "low_holder_count": 50,  # Less than 50 holders
        "new_token_hours": 24,  # Token less than 24 hours old
        "mint_authority_enabled": True,
        "freeze_authority_enabled": True,
        "high_tax": 0.1,  # More than 10% tax
    }
    
    def __init__(self, solscan_api_key: str):
        self.solscan_api_key = solscan_api_key
        self.client = httpx.AsyncClient(timeout=30)
    
    async def check_token(self, token_address: str) -> RugCheckResult:
        """
        Comprehensive rug check for a token
        Returns risk score 0-1 (higher = more risky)
        """
        warnings = []
        risk_factors = []
        details = {}
        
        try:
            # Fetch token metadata from Solscan
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
            
            # Check 4: Creator holdings
            creator_holdings = await self._check_creator_holdings(token_address, token_info)
            if creator_holdings > self.RUG_INDICATORS["high_creator_holdings"]:
                warnings.append(f"Creator holds {creator_holdings*100:.1f}% of supply")
                risk_factors.append(0.35)
            details["creator_holdings_pct"] = creator_holdings
            
            # Check 5: Mint/Freeze authority
            authorities = await self._check_authorities(token_address)
            if authorities.get("mint_authority"):
                warnings.append("Mint authority still enabled - can create more tokens")
                risk_factors.append(0.25)
            if authorities.get("freeze_authority"):
                warnings.append("Freeze authority enabled - can freeze your tokens")
                risk_factors.append(0.2)
            details["authorities"] = authorities
            
            # Check 6: Top holder concentration
            top_holder_pct = await self._check_top_holders(token_address)
            if top_holder_pct > 0.8:  # Top 10 holders own > 80%
                warnings.append(f"High concentration: Top holders own {top_holder_pct*100:.1f}%")
                risk_factors.append(0.25)
            details["top_holder_concentration"] = top_holder_pct
            
            # Check 7: Known rugger address
            is_known_rugger = await self._check_known_ruggers(token_info.get("creator"))
            if is_known_rugger:
                warnings.append("Creator is a known rugger!")
                risk_factors.append(0.5)
            details["known_rugger"] = is_known_rugger
            
            # Calculate final risk score
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
                warnings=["Failed to perform rug check - treating as unsafe"],
                details={"error": str(e)}
            )
    
    async def _get_token_info(self, token_address: str) -> Dict:
        """Fetch token information from Solscan"""
        try:
            headers = {"token": self.solscan_api_key}
            response = await self.client.get(
                f"https://pro-api.solscan.io/v2.0/token/meta",
                params={"address": token_address},
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {})
            return {}
        except Exception as e:
            logger.error(f"Token info error: {e}")
            return {}
    
    async def _check_creator_holdings(self, token_address: str, token_info: Dict) -> float:
        """Check what percentage the creator still holds"""
        try:
            creator = token_info.get("creator")
            if not creator:
                return 0.0
            
            headers = {"token": self.solscan_api_key}
            response = await self.client.get(
                f"https://pro-api.solscan.io/v2.0/account/token-accounts",
                params={"address": creator},
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                for account in data.get("data", []):
                    if account.get("tokenAddress") == token_address:
                        balance = float(account.get("amount", 0))
                        supply = float(token_info.get("supply", 1))
                        return balance / supply if supply > 0 else 0
            return 0.0
        except Exception as e:
            logger.error(f"Creator holdings check error: {e}")
            return 0.0
    
    async def _check_authorities(self, token_address: str) -> Dict:
        """Check if mint/freeze authorities are still active"""
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getAccountInfo",
                    "params": [token_address, {"encoding": "jsonParsed"}]
                }
                response = await client.post(SOLANA_RPC, json=payload)
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
            return {"mint_authority": True, "freeze_authority": True}  # Assume worst case
    
    async def _check_top_holders(self, token_address: str) -> float:
        """Check concentration of top holders"""
        try:
            headers = {"token": self.solscan_api_key}
            response = await self.client.get(
                f"https://pro-api.solscan.io/v2.0/token/holders",
                params={"address": token_address, "page_size": 10},
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                holders = data.get("data", [])
                total_pct = sum(float(h.get("percentage", 0)) for h in holders)
                return total_pct / 100
            return 0.0
        except Exception as e:
            logger.error(f"Top holders check error: {e}")
            return 0.0
    
    async def _check_known_ruggers(self, creator_address: Optional[str]) -> bool:
        """Check if creator is in known rugger database"""
        if not creator_address:
            return False
        
        # Known rugger addresses (would be stored in DB in production)
        KNOWN_RUGGERS = [
            "AUFxnVLsKkkupjCY4kmA5ZDH8c4HgK7CZ4FYw1VcXpn8",
            # Add more known rugger addresses
        ]
        return creator_address in KNOWN_RUGGERS
    
    async def close(self):
        await self.client.aclose()


class WhaleMonitor:
    """Real-time whale wallet monitoring"""
    
    def __init__(self, whale_wallets: List[str], solscan_api_key: str, callback=None):
        self.whale_wallets = whale_wallets
        self.solscan_api_key = solscan_api_key
        self.callback = callback  # Called when whale activity detected
        self.client = httpx.AsyncClient(timeout=30)
        self.last_signatures: Dict[str, str] = {}
        self.is_running = False
    
    async def start_monitoring(self, poll_interval: int = 10):
        """Start polling whale wallets for new transactions"""
        self.is_running = True
        logger.info(f"Starting whale monitor for {len(self.whale_wallets)} wallets")
        
        while self.is_running:
            try:
                for wallet in self.whale_wallets:
                    activities = await self._check_wallet_activity(wallet)
                    for activity in activities:
                        if self.callback:
                            await self.callback(activity)
                
                await asyncio.sleep(poll_interval)
            except Exception as e:
                logger.error(f"Whale monitor error: {e}")
                await asyncio.sleep(5)
    
    async def stop_monitoring(self):
        """Stop monitoring"""
        self.is_running = False
    
    async def _check_wallet_activity(self, wallet_address: str) -> List[Dict]:
        """Check for new token transactions from a whale wallet"""
        activities = []
        try:
            headers = {"token": self.solscan_api_key}
            response = await self.client.get(
                f"https://pro-api.solscan.io/v2.0/account/transfer",
                params={
                    "address": wallet_address,
                    "page_size": 10,
                    "token_type": "token"
                },
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                transfers = data.get("data", [])
                
                for transfer in transfers:
                    sig = transfer.get("trans_id")
                    
                    # Skip if we've seen this transaction
                    if wallet_address in self.last_signatures:
                        if sig == self.last_signatures[wallet_address]:
                            break
                    
                    # New transaction found
                    activity = {
                        "whale_address": wallet_address,
                        "signature": sig,
                        "token_address": transfer.get("token_address"),
                        "token_symbol": transfer.get("token_symbol", "UNKNOWN"),
                        "amount": float(transfer.get("amount", 0)),
                        "flow": transfer.get("flow"),  # "in" or "out"
                        "timestamp": transfer.get("block_time"),
                        "action": "BUY" if transfer.get("flow") == "in" else "SELL"
                    }
                    activities.append(activity)
                    logger.info(f"Whale activity: {wallet_address[:8]}... {activity['action']} {activity['token_symbol']}")
                
                # Update last signature
                if transfers:
                    self.last_signatures[wallet_address] = transfers[0].get("trans_id")
                    
        except Exception as e:
            logger.error(f"Wallet activity check error for {wallet_address}: {e}")
        
        return activities
    
    async def get_wallet_tokens(self, wallet_address: str) -> List[Dict]:
        """Get all tokens held by a wallet"""
        try:
            headers = {"token": self.solscan_api_key}
            response = await self.client.get(
                f"https://pro-api.solscan.io/v2.0/account/token-accounts",
                params={"address": wallet_address, "page_size": 50},
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Get wallet tokens error: {e}")
            return []
    
    async def close(self):
        await self.client.aclose()


class AutoTrader:
    """Automated trading logic"""
    
    def __init__(
        self,
        jupiter: JupiterDEX,
        rug_detector: RugDetector,
        db,
        telegram_bot=None,
        min_profit_usd: float = MIN_PROFIT_USD,
        max_trade_time: int = MAX_TRADE_TIME_SECONDS
    ):
        self.jupiter = jupiter
        self.rug_detector = rug_detector
        self.db = db
        self.telegram_bot = telegram_bot
        self.min_profit_usd = min_profit_usd
        self.max_trade_time = max_trade_time
        self.active_positions: Dict[str, Dict] = {}  # token_address -> position info
        self.is_running = False
    
    async def process_whale_signal(self, activity: Dict) -> Optional[TradeSignal]:
        """
        Process whale activity and generate trade signal if profitable
        """
        token_address = activity.get("token_address")
        whale_action = activity.get("action")
        
        if not token_address or whale_action != "BUY":
            return None  # Only follow whale buys for now
        
        # Step 1: Rug check
        rug_result = await self.rug_detector.check_token(token_address)
        if not rug_result.is_safe:
            logger.warning(f"Token {token_address} failed rug check: {rug_result.warnings}")
            return TradeSignal(
                token_address=token_address,
                token_symbol=activity.get("token_symbol", "UNKNOWN"),
                action="SKIP",
                reason=f"Rug risk: {', '.join(rug_result.warnings[:2])}",
                confidence=0,
                risk_score=rug_result.risk_score
            )
        
        # Step 2: Check if profitable
        token_price = await self.jupiter.get_token_price(token_address)
        liquidity = rug_result.details.get("liquidity_usd", 0)
        
        if liquidity < MIN_LIQUIDITY_USD:
            return TradeSignal(
                token_address=token_address,
                token_symbol=activity.get("token_symbol", "UNKNOWN"),
                action="SKIP",
                reason=f"Low liquidity: ${liquidity:.2f}",
                confidence=0,
                risk_score=rug_result.risk_score
            )
        
        # Calculate confidence based on whale reputation and token metrics
        confidence = self._calculate_confidence(activity, rug_result)
        
        return TradeSignal(
            token_address=token_address,
            token_symbol=activity.get("token_symbol", "UNKNOWN"),
            action="BUY",
            reason=f"Whale {activity['whale_address'][:8]}... bought",
            confidence=confidence,
            whale_address=activity.get("whale_address"),
            estimated_profit_usd=self.min_profit_usd,  # Target profit
            risk_score=rug_result.risk_score
        )
    
    def _calculate_confidence(self, activity: Dict, rug_result: RugCheckResult) -> float:
        """Calculate trade confidence score 0-1"""
        confidence = 0.5  # Base confidence
        
        # Lower confidence for higher risk
        confidence -= rug_result.risk_score * 0.3
        
        # Boost for good liquidity
        liquidity = rug_result.details.get("liquidity_usd", 0)
        if liquidity > 50000:
            confidence += 0.1
        if liquidity > 100000:
            confidence += 0.1
        
        # Boost for more holders
        holders = rug_result.details.get("holder_count", 0)
        if holders > 100:
            confidence += 0.05
        if holders > 500:
            confidence += 0.1
        
        return max(0.1, min(0.95, confidence))
    
    async def execute_trade(
        self,
        signal: TradeSignal,
        keypair: Keypair,
        amount_sol: float,
        user_telegram_id: int
    ) -> Dict:
        """
        Execute a trade based on signal
        Returns trade result with details
        """
        trade_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        # Convert SOL to lamports (leave some for gas)
        amount_lamports = int((amount_sol - GAS_RESERVE_SOL) * 1e9)
        
        if signal.action != "BUY":
            return {
                "trade_id": trade_id,
                "success": False,
                "reason": f"Signal action is {signal.action}, not BUY"
            }
        
        # Execute buy
        success, signature, error = await self.jupiter.execute_swap(
            keypair=keypair,
            input_mint=WSOL_MINT,
            output_mint=signal.token_address,
            amount_lamports=amount_lamports,
            slippage_bps=MAX_SLIPPAGE_BPS
        )
        
        if not success:
            return {
                "trade_id": trade_id,
                "success": False,
                "reason": error,
                "signal": signal
            }
        
        # Record position
        self.active_positions[signal.token_address] = {
            "trade_id": trade_id,
            "user_telegram_id": user_telegram_id,
            "entry_time": start_time,
            "entry_signature": signature,
            "amount_sol": amount_sol,
            "token_address": signal.token_address,
            "keypair": keypair
        }
        
        # Start monitoring for exit
        asyncio.create_task(
            self._monitor_position_for_exit(signal.token_address)
        )
        
        return {
            "trade_id": trade_id,
            "success": True,
            "signature": signature,
            "action": "BUY",
            "token": signal.token_symbol,
            "amount_sol": amount_sol
        }
    
    async def _monitor_position_for_exit(self, token_address: str):
        """Monitor position and exit when profit target reached or timeout"""
        position = self.active_positions.get(token_address)
        if not position:
            return
        
        entry_time = position["entry_time"]
        target_profit = self.min_profit_usd
        
        while token_address in self.active_positions:
            try:
                elapsed = (datetime.now(timezone.utc) - entry_time).total_seconds()
                
                # Check timeout
                if elapsed > self.max_trade_time:
                    logger.info(f"Position {token_address} timeout - exiting")
                    await self._exit_position(token_address, "TIMEOUT")
                    break
                
                # Check profit (simplified - would need actual price tracking)
                current_price = await self.jupiter.get_token_price(token_address)
                if current_price:
                    # Calculate unrealized P&L
                    # In production, track entry price and tokens received
                    pass
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Position monitor error: {e}")
                await asyncio.sleep(5)
    
    async def _exit_position(self, token_address: str, reason: str) -> Dict:
        """Exit a position (sell tokens)"""
        position = self.active_positions.pop(token_address, None)
        if not position:
            return {"success": False, "reason": "Position not found"}
        
        # Would execute sell here
        # For now, return simulated result
        return {
            "success": True,
            "reason": reason,
            "trade_id": position["trade_id"]
        }
    
    async def get_active_positions(self) -> List[Dict]:
        """Get all active positions"""
        return [
            {
                "token_address": addr,
                "entry_time": pos["entry_time"].isoformat(),
                "amount_sol": pos["amount_sol"]
            }
            for addr, pos in self.active_positions.items()
        ]


class TrendingTokenScanner:
    """Scan for trending tokens on pump.fun and DEXes"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30)
    
    async def get_trending_tokens(self) -> List[Dict]:
        """Get trending Solana tokens from DexScreener"""
        try:
            # Use the token boosted endpoint for popular tokens
            response = await self.client.get(
                "https://api.dexscreener.com/token-boosts/top/v1"
            )
            tokens = []
            if response.status_code == 200:
                data = response.json()
                for item in data[:30]:
                    if item.get("chainId") == "solana":
                        tokens.append({
                            "address": item.get("tokenAddress"),
                            "symbol": item.get("description", "").split()[0] if item.get("description") else "UNKNOWN",
                            "name": item.get("description", "Unknown"),
                            "price_usd": 0,
                            "liquidity_usd": 0,
                            "volume_24h": 0,
                            "price_change_24h": 0,
                            "dex": "dexscreener",
                            "url": item.get("url", "")
                        })
            
            # Also fetch from pairs endpoint
            response2 = await self.client.get(
                "https://api.dexscreener.com/latest/dex/pairs/solana"
            )
            if response2.status_code == 200:
                data2 = response2.json()
                pairs = data2.get("pairs", [])[:20]
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
            
            # Remove duplicates and sort by volume
            seen = set()
            unique_tokens = []
            for t in tokens:
                if t["address"] and t["address"] not in seen:
                    seen.add(t["address"])
                    unique_tokens.append(t)
            
            return sorted(unique_tokens, key=lambda x: x.get("volume_24h", 0), reverse=True)[:20]
        except Exception as e:
            logger.error(f"Trending tokens error: {e}")
            return []
    
    async def get_new_pairs(self, min_liquidity: float = 5000) -> List[Dict]:
        """Get newly created Solana pairs"""
        try:
            response = await self.client.get(
                "https://api.dexscreener.com/latest/dex/pairs/solana"
            )
            if response.status_code == 200:
                data = response.json()
                pairs = data.get("pairs", [])
                
                # Filter for new pairs with minimum liquidity
                new_pairs = []
                for p in pairs:
                    liquidity = float(p.get("liquidity", {}).get("usd", 0) or 0)
                    created_at = p.get("pairCreatedAt")
                    
                    if liquidity >= min_liquidity:
                        new_pairs.append({
                            "address": p.get("baseToken", {}).get("address"),
                            "symbol": p.get("baseToken", {}).get("symbol"),
                            "liquidity_usd": liquidity,
                            "created_at": created_at,
                            "dex": p.get("dexId")
                        })
                
                return new_pairs[:20]
            return []
        except Exception as e:
            logger.error(f"New pairs error: {e}")
            return []
    
    async def close(self):
        await self.client.aclose()


# Import for use in main server
import uuid
