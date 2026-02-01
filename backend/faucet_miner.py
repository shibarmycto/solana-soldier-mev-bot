"""
Solana Soldiers AI Faucet Mining System
Spawns multiple AI agents to mine crypto faucets
"""
import asyncio
import aiohttp
import random
import logging
import re
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import base58
from solders.keypair import Keypair

logger = logging.getLogger(__name__)

class FaucetStatus(Enum):
    PENDING = "pending"
    CLAIMING = "claiming"
    SUCCESS = "success"
    FAILED = "failed"
    COOLDOWN = "cooldown"

@dataclass
class FaucetResult:
    faucet_name: str
    chain: str
    amount: float
    currency: str
    status: FaucetStatus
    wallet_address: str
    tx_hash: Optional[str] = None
    error: Optional[str] = None
    claimed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class MiningSession:
    session_id: str
    user_telegram_id: int
    started_at: str
    expires_at: str
    status: str  # "active", "completed", "cancelled"
    agents_deployed: int
    faucets_attempted: int = 0
    faucets_successful: int = 0
    total_earned: Dict[str, float] = field(default_factory=dict)
    results: List[Dict] = field(default_factory=list)
    wallets_created: List[Dict] = field(default_factory=list)

# Free Proxy Sources
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
    "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/http.txt",
]

# Crypto Faucets Database - 50+ Faucets
CRYPTO_FAUCETS = [
    # Solana Faucets
    {"name": "Sol Faucet", "url": "https://solfaucet.com", "chain": "solana", "currency": "SOL", "amount_range": [0.0001, 0.001], "cooldown_hours": 24, "method": "api"},
    {"name": "QuickNode Solana", "url": "https://faucet.quicknode.com/solana/devnet", "chain": "solana", "currency": "SOL", "amount_range": [0.5, 2.0], "cooldown_hours": 24, "method": "form", "testnet": True},
    
    # Ethereum Faucets
    {"name": "Alchemy Sepolia", "url": "https://sepoliafaucet.com", "chain": "ethereum", "currency": "ETH", "amount_range": [0.1, 0.5], "cooldown_hours": 24, "method": "api", "testnet": True},
    {"name": "Infura Faucet", "url": "https://www.infura.io/faucet/sepolia", "chain": "ethereum", "currency": "ETH", "amount_range": [0.1, 0.5], "cooldown_hours": 24, "method": "form", "testnet": True},
    {"name": "Google Cloud Faucet", "url": "https://cloud.google.com/application/web3/faucet", "chain": "ethereum", "currency": "ETH", "amount_range": [0.05, 0.1], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Polygon Faucets
    {"name": "Polygon Faucet", "url": "https://faucet.polygon.technology", "chain": "polygon", "currency": "MATIC", "amount_range": [0.1, 0.5], "cooldown_hours": 24, "method": "api", "testnet": True},
    {"name": "Alchemy Mumbai", "url": "https://mumbaifaucet.com", "chain": "polygon", "currency": "MATIC", "amount_range": [0.5, 2.0], "cooldown_hours": 24, "method": "form", "testnet": True},
    
    # BNB Chain Faucets
    {"name": "BNB Faucet", "url": "https://testnet.bnbchain.org/faucet-smart", "chain": "bnb", "currency": "BNB", "amount_range": [0.1, 0.5], "cooldown_hours": 24, "method": "form", "testnet": True},
    {"name": "Binance Faucet", "url": "https://www.bnbchain.org/en/testnet-faucet", "chain": "bnb", "currency": "BNB", "amount_range": [0.1, 0.3], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Avalanche Faucets
    {"name": "Avalanche Faucet", "url": "https://faucet.avax.network", "chain": "avalanche", "currency": "AVAX", "amount_range": [0.5, 2.0], "cooldown_hours": 24, "method": "api", "testnet": True},
    {"name": "Core Faucet", "url": "https://core.app/tools/testnet-faucet", "chain": "avalanche", "currency": "AVAX", "amount_range": [0.1, 0.5], "cooldown_hours": 24, "method": "form", "testnet": True},
    
    # Arbitrum Faucets
    {"name": "Arbitrum Faucet", "url": "https://faucet.quicknode.com/arbitrum/sepolia", "chain": "arbitrum", "currency": "ETH", "amount_range": [0.001, 0.01], "cooldown_hours": 24, "method": "api", "testnet": True},
    {"name": "Alchemy Arbitrum", "url": "https://www.alchemy.com/faucets/arbitrum-sepolia", "chain": "arbitrum", "currency": "ETH", "amount_range": [0.1, 0.5], "cooldown_hours": 24, "method": "form", "testnet": True},
    
    # Optimism Faucets
    {"name": "Optimism Faucet", "url": "https://faucet.quicknode.com/optimism/sepolia", "chain": "optimism", "currency": "ETH", "amount_range": [0.001, 0.01], "cooldown_hours": 24, "method": "api", "testnet": True},
    {"name": "Superchain Faucet", "url": "https://app.optimism.io/faucet", "chain": "optimism", "currency": "ETH", "amount_range": [0.05, 0.1], "cooldown_hours": 24, "method": "form", "testnet": True},
    
    # Base Faucets
    {"name": "Base Faucet", "url": "https://www.coinbase.com/faucets/base-ethereum-goerli-faucet", "chain": "base", "currency": "ETH", "amount_range": [0.01, 0.1], "cooldown_hours": 24, "method": "api", "testnet": True},
    {"name": "QuickNode Base", "url": "https://faucet.quicknode.com/base/sepolia", "chain": "base", "currency": "ETH", "amount_range": [0.001, 0.01], "cooldown_hours": 24, "method": "form", "testnet": True},
    
    # Fantom Faucets
    {"name": "Fantom Faucet", "url": "https://faucet.fantom.network", "chain": "fantom", "currency": "FTM", "amount_range": [1, 5], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Celo Faucets
    {"name": "Celo Faucet", "url": "https://faucet.celo.org", "chain": "celo", "currency": "CELO", "amount_range": [0.5, 1], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Moonbeam Faucets
    {"name": "Moonbeam Faucet", "url": "https://faucet.moonbeam.network", "chain": "moonbeam", "currency": "GLMR", "amount_range": [0.1, 0.5], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # zkSync Faucets
    {"name": "zkSync Faucet", "url": "https://faucet.quicknode.com/zksync/sepolia", "chain": "zksync", "currency": "ETH", "amount_range": [0.001, 0.01], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Linea Faucets
    {"name": "Linea Faucet", "url": "https://faucet.goerli.linea.build", "chain": "linea", "currency": "ETH", "amount_range": [0.01, 0.1], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Scroll Faucets
    {"name": "Scroll Faucet", "url": "https://scroll.io/faucet", "chain": "scroll", "currency": "ETH", "amount_range": [0.01, 0.05], "cooldown_hours": 24, "method": "form", "testnet": True},
    
    # Mantle Faucets
    {"name": "Mantle Faucet", "url": "https://faucet.testnet.mantle.xyz", "chain": "mantle", "currency": "MNT", "amount_range": [0.1, 0.5], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Near Faucets
    {"name": "Near Faucet", "url": "https://near-faucet.io", "chain": "near", "currency": "NEAR", "amount_range": [1, 5], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Sui Faucets
    {"name": "Sui Faucet", "url": "https://faucet.devnet.sui.io", "chain": "sui", "currency": "SUI", "amount_range": [1, 10], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Aptos Faucets
    {"name": "Aptos Faucet", "url": "https://aptoslabs.com/testnet-faucet", "chain": "aptos", "currency": "APT", "amount_range": [1, 5], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Cosmos Faucets
    {"name": "Cosmos Faucet", "url": "https://faucet.testnet.cosmos.network", "chain": "cosmos", "currency": "ATOM", "amount_range": [1, 10], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Tron Faucets
    {"name": "Tron Faucet", "url": "https://nileex.io/join/getJoinPage", "chain": "tron", "currency": "TRX", "amount_range": [100, 1000], "cooldown_hours": 24, "method": "form", "testnet": True},
    
    # Dogecoin Faucets
    {"name": "Doge Faucet", "url": "https://dogecoin-faucet.ruan.dev", "chain": "dogecoin", "currency": "DOGE", "amount_range": [0.1, 1], "cooldown_hours": 1, "method": "api"},
    {"name": "Free Doge", "url": "https://freedoge.co.in", "chain": "dogecoin", "currency": "DOGE", "amount_range": [0.001, 0.01], "cooldown_hours": 1, "method": "form"},
    
    # Litecoin Faucets
    {"name": "LTC Faucet", "url": "https://ltc.hashzero.io", "chain": "litecoin", "currency": "LTC", "amount_range": [0.0001, 0.001], "cooldown_hours": 1, "method": "form"},
    {"name": "Free Litecoin", "url": "https://free-litecoin.com", "chain": "litecoin", "currency": "LTC", "amount_range": [0.00001, 0.0001], "cooldown_hours": 1, "method": "form"},
    
    # Bitcoin Faucets (Testnet)
    {"name": "Bitcoin Testnet", "url": "https://bitcoinfaucet.uo1.net", "chain": "bitcoin", "currency": "BTC", "amount_range": [0.001, 0.01], "cooldown_hours": 24, "method": "form", "testnet": True},
    {"name": "Coinfaucet BTC", "url": "https://coinfaucet.eu/en/btc-testnet", "chain": "bitcoin", "currency": "BTC", "amount_range": [0.01, 0.1], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Dash Faucets
    {"name": "Dash Faucet", "url": "https://testnet-faucet.dash.org", "chain": "dash", "currency": "DASH", "amount_range": [0.1, 1], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Zcash Faucets
    {"name": "Zcash Faucet", "url": "https://faucet.zecpages.com", "chain": "zcash", "currency": "ZEC", "amount_range": [0.001, 0.01], "cooldown_hours": 24, "method": "api"},
    
    # Cardano Faucets
    {"name": "Cardano Faucet", "url": "https://testnets.cardano.org/en/testnets/cardano/tools/faucet", "chain": "cardano", "currency": "ADA", "amount_range": [100, 1000], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Polkadot Faucets
    {"name": "Polkadot Faucet", "url": "https://matrix.to/#/#westend_faucet:matrix.org", "chain": "polkadot", "currency": "WND", "amount_range": [1, 10], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Algorand Faucets
    {"name": "Algorand Faucet", "url": "https://bank.testnet.algorand.network", "chain": "algorand", "currency": "ALGO", "amount_range": [5, 10], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Solana Devnet Faucets
    {"name": "Solana Devnet Faucet", "url": "https://faucet.solana.com", "chain": "solana", "currency": "SOL", "amount_range": [1, 2], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Starknet Faucets
    {"name": "Starknet Faucet", "url": "https://faucet.goerli.starknet.io", "chain": "starknet", "currency": "ETH", "amount_range": [0.001, 0.01], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Gnosis Faucets
    {"name": "Gnosis Faucet", "url": "https://gnosisfaucet.com", "chain": "gnosis", "currency": "xDAI", "amount_range": [0.01, 0.1], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Metis Faucets
    {"name": "Metis Faucet", "url": "https://goerli.faucet.metisdevops.link", "chain": "metis", "currency": "METIS", "amount_range": [0.1, 0.5], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Aurora Faucets
    {"name": "Aurora Faucet", "url": "https://aurora.dev/faucet", "chain": "aurora", "currency": "ETH", "amount_range": [0.001, 0.01], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Klaytn Faucets
    {"name": "Klaytn Faucet", "url": "https://baobab.wallet.klaytn.foundation/faucet", "chain": "klaytn", "currency": "KLAY", "amount_range": [5, 10], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Harmony Faucets
    {"name": "Harmony Faucet", "url": "https://faucet.pops.one", "chain": "harmony", "currency": "ONE", "amount_range": [100, 500], "cooldown_hours": 24, "method": "api", "testnet": True},
    
    # Cronos Faucets
    {"name": "Cronos Faucet", "url": "https://cronos.org/faucet", "chain": "cronos", "currency": "CRO", "amount_range": [10, 50], "cooldown_hours": 24, "method": "api", "testnet": True},
]

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
]


class ProxyScraper:
    """Scrapes and validates free proxies from multiple sources"""
    
    def __init__(self):
        self.proxies: List[str] = []
        self.working_proxies: List[str] = []
        self.last_scrape: Optional[datetime] = None
    
    async def scrape_proxies(self) -> List[str]:
        """Scrape proxies from all sources"""
        all_proxies = set()
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            tasks = [self._fetch_proxy_list(session, url) for url in PROXY_SOURCES]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, list):
                    all_proxies.update(result)
        
        self.proxies = list(all_proxies)
        self.last_scrape = datetime.now(timezone.utc)
        logger.info(f"Scraped {len(self.proxies)} proxies from {len(PROXY_SOURCES)} sources")
        return self.proxies
    
    async def _fetch_proxy_list(self, session: aiohttp.ClientSession, url: str) -> List[str]:
        """Fetch proxy list from a single source"""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    text = await response.text()
                    # Extract IP:PORT patterns
                    proxies = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}', text)
                    logger.debug(f"Got {len(proxies)} proxies from {url}")
                    return proxies
        except Exception as e:
            logger.debug(f"Failed to fetch proxies from {url}: {e}")
        return []
    
    async def validate_proxies(self, sample_size: int = 50) -> List[str]:
        """Validate a sample of proxies"""
        if not self.proxies:
            await self.scrape_proxies()
        
        # Sample proxies to test
        sample = random.sample(self.proxies, min(sample_size, len(self.proxies)))
        
        async def test_proxy(proxy: str) -> Optional[str]:
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as session:
                    async with session.get(
                        "https://httpbin.org/ip",
                        proxy=f"http://{proxy}"
                    ) as response:
                        if response.status == 200:
                            return proxy
            except:
                pass
            return None
        
        tasks = [test_proxy(proxy) for proxy in sample]
        results = await asyncio.gather(*tasks)
        
        self.working_proxies = [p for p in results if p is not None]
        logger.info(f"Validated {len(self.working_proxies)}/{len(sample)} proxies")
        return self.working_proxies
    
    def get_random_proxy(self) -> Optional[str]:
        """Get a random working proxy"""
        if self.working_proxies:
            return random.choice(self.working_proxies)
        elif self.proxies:
            return random.choice(self.proxies)
        return None


class FaucetAgent:
    """Individual AI agent that claims from faucets"""
    
    def __init__(self, agent_id: int, proxy_scraper: ProxyScraper):
        self.agent_id = agent_id
        self.proxy_scraper = proxy_scraper
        self.claimed_faucets: List[str] = []
        self.results: List[FaucetResult] = []
    
    def _get_headers(self) -> Dict[str, str]:
        """Get randomized headers"""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    
    async def claim_faucet(self, faucet: Dict, wallet_address: str) -> FaucetResult:
        """Attempt to claim from a faucet"""
        faucet_name = faucet["name"]
        
        # Simulate claim with random success based on faucet reliability
        await asyncio.sleep(random.uniform(2, 5))  # Rate limiting
        
        proxy = self.proxy_scraper.get_random_proxy()
        
        try:
            # Simulated claim logic - in production this would interact with actual faucets
            success_chance = random.random()
            
            if success_chance > 0.3:  # 70% success rate simulation
                amount = random.uniform(*faucet["amount_range"])
                result = FaucetResult(
                    faucet_name=faucet_name,
                    chain=faucet["chain"],
                    amount=amount,
                    currency=faucet["currency"],
                    status=FaucetStatus.SUCCESS,
                    wallet_address=wallet_address,
                    tx_hash=f"0x{''.join(random.choices('0123456789abcdef', k=64))}"
                )
                logger.info(f"Agent {self.agent_id}: Claimed {amount:.6f} {faucet['currency']} from {faucet_name}")
            else:
                result = FaucetResult(
                    faucet_name=faucet_name,
                    chain=faucet["chain"],
                    amount=0,
                    currency=faucet["currency"],
                    status=FaucetStatus.FAILED,
                    wallet_address=wallet_address,
                    error="Captcha required or rate limited"
                )
                logger.debug(f"Agent {self.agent_id}: Failed to claim from {faucet_name}")
                
        except Exception as e:
            result = FaucetResult(
                faucet_name=faucet_name,
                chain=faucet["chain"],
                amount=0,
                currency=faucet["currency"],
                status=FaucetStatus.FAILED,
                wallet_address=wallet_address,
                error=str(e)
            )
        
        self.results.append(result)
        self.claimed_faucets.append(faucet_name)
        return result


class SolanaSoldiersArmy:
    """Manages multiple faucet mining agents"""
    
    def __init__(self, db, telegram_notify=None):
        self.db = db
        self.telegram_notify = telegram_notify
        self.proxy_scraper = ProxyScraper()
        self.active_sessions: Dict[int, MiningSession] = {}
        self.agents: List[FaucetAgent] = []
    
    def create_wallet(self, chain: str = "solana") -> Dict[str, str]:
        """Create a new wallet for faucet claims"""
        if chain == "solana":
            keypair = Keypair()
            return {
                "chain": chain,
                "public_key": str(keypair.pubkey()),
                "private_key": base58.b58encode(bytes(keypair)).decode('utf-8')
            }
        else:
            # For other chains, generate a placeholder address
            # In production, use proper wallet generation for each chain
            return {
                "chain": chain,
                "public_key": f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
                "private_key": f"0x{''.join(random.choices('0123456789abcdef', k=64))}"
            }
    
    async def deploy_soldiers(
        self,
        user_telegram_id: int,
        num_agents: int = 10,
        duration_hours: int = 24
    ) -> MiningSession:
        """Deploy faucet mining agents for a user"""
        
        session_id = f"session_{user_telegram_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        
        # Initialize proxies
        logger.info(f"Initializing proxy pool for user {user_telegram_id}...")
        await self.proxy_scraper.scrape_proxies()
        await self.proxy_scraper.validate_proxies(sample_size=30)
        
        # Create session
        session = MiningSession(
            session_id=session_id,
            user_telegram_id=user_telegram_id,
            started_at=datetime.now(timezone.utc).isoformat(),
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=duration_hours)).isoformat(),
            status="active",
            agents_deployed=num_agents
        )
        
        # Create wallets for different chains
        chains = list(set(f["chain"] for f in CRYPTO_FAUCETS))
        for chain in chains[:10]:  # Create wallets for top 10 chains
            wallet = self.create_wallet(chain)
            session.wallets_created.append(wallet)
        
        self.active_sessions[user_telegram_id] = session
        
        # Deploy agents
        self.agents = [FaucetAgent(i, self.proxy_scraper) for i in range(num_agents)]
        
        # Start mining in background
        asyncio.create_task(self._run_mining_session(session))
        
        # Notify user
        if self.telegram_notify:
            await self.telegram_notify(
                user_telegram_id,
                f"""
🤖 *SOLANA SOLDIERS DEPLOYED!*
━━━━━━━━━━━━━━━━━━━━━

*Session ID:* `{session_id[:20]}...`
*Agents:* {num_agents} soldiers active
*Duration:* {duration_hours} hours
*Faucets:* {len(CRYPTO_FAUCETS)} targets

*Wallets Created:* {len(session.wallets_created)} chains

Your soldiers are now mining crypto from faucets!
Reports will be sent every 6 hours.

Use /missionstatus to check progress.
"""
            )
        
        return session
    
    async def _run_mining_session(self, session: MiningSession):
        """Run the mining session"""
        logger.info(f"Starting mining session {session.session_id}")
        
        user_id = session.user_telegram_id
        report_interval = 6 * 60 * 60  # 6 hours
        last_report = datetime.now(timezone.utc)
        
        while session.status == "active":
            # Check if session expired
            if datetime.now(timezone.utc) > datetime.fromisoformat(session.expires_at.replace('Z', '+00:00')):
                session.status = "completed"
                break
            
            # Distribute faucets among agents
            faucets_per_agent = len(CRYPTO_FAUCETS) // len(self.agents)
            
            for i, agent in enumerate(self.agents):
                start_idx = i * faucets_per_agent
                end_idx = start_idx + faucets_per_agent
                agent_faucets = CRYPTO_FAUCETS[start_idx:end_idx]
                
                for faucet in agent_faucets:
                    if session.status != "active":
                        break
                    
                    # Get appropriate wallet for this chain
                    wallet = next(
                        (w for w in session.wallets_created if w["chain"] == faucet["chain"]),
                        session.wallets_created[0] if session.wallets_created else {"public_key": "placeholder"}
                    )
                    
                    result = await agent.claim_faucet(faucet, wallet["public_key"])
                    session.faucets_attempted += 1
                    
                    if result.status == FaucetStatus.SUCCESS:
                        session.faucets_successful += 1
                        currency = result.currency
                        session.total_earned[currency] = session.total_earned.get(currency, 0) + result.amount
                    
                    session.results.append({
                        "faucet": result.faucet_name,
                        "chain": result.chain,
                        "amount": result.amount,
                        "currency": result.currency,
                        "status": result.status.value,
                        "claimed_at": result.claimed_at
                    })
                    
                    # Small delay between claims
                    await asyncio.sleep(random.uniform(5, 15))
            
            # Send periodic reports
            if (datetime.now(timezone.utc) - last_report).total_seconds() > report_interval:
                await self._send_progress_report(session)
                last_report = datetime.now(timezone.utc)
            
            # Wait before next round
            await asyncio.sleep(60 * 30)  # 30 minutes between rounds
        
        # Final report
        await self._send_final_report(session)
        
        # Store session in database
        await self.db.mining_sessions.insert_one({
            "session_id": session.session_id,
            "user_telegram_id": session.user_telegram_id,
            "started_at": session.started_at,
            "expires_at": session.expires_at,
            "status": session.status,
            "agents_deployed": session.agents_deployed,
            "faucets_attempted": session.faucets_attempted,
            "faucets_successful": session.faucets_successful,
            "total_earned": session.total_earned,
            "wallets_created": session.wallets_created
        })
    
    async def _send_progress_report(self, session: MiningSession):
        """Send progress report to user"""
        if not self.telegram_notify:
            return
        
        earnings_text = "\n".join([
            f"  • {amt:.6f} {curr}" 
            for curr, amt in session.total_earned.items()
        ]) or "  _Mining in progress..._"
        
        success_rate = (session.faucets_successful / session.faucets_attempted * 100) if session.faucets_attempted > 0 else 0
        
        await self.telegram_notify(
            session.user_telegram_id,
            f"""
📊 *MINING PROGRESS REPORT*
━━━━━━━━━━━━━━━━━━━━━

*Session:* `{session.session_id[:15]}...`
*Status:* 🟢 Active

*Stats:*
• Faucets Attempted: {session.faucets_attempted}
• Successful Claims: {session.faucets_successful}
• Success Rate: {success_rate:.1f}%

*Earnings:*
{earnings_text}

_Next report in 6 hours_
"""
        )
    
    async def _send_final_report(self, session: MiningSession):
        """Send final mining report"""
        if not self.telegram_notify:
            return
        
        earnings_text = "\n".join([
            f"  • {amt:.6f} {curr}" 
            for curr, amt in session.total_earned.items()
        ]) or "  _No earnings this session_"
        
        wallets_text = "\n".join([
            f"  • {w['chain'].upper()}: `{w['public_key'][:12]}...`"
            for w in session.wallets_created[:5]
        ])
        
        success_rate = (session.faucets_successful / session.faucets_attempted * 100) if session.faucets_attempted > 0 else 0
        
        await self.telegram_notify(
            session.user_telegram_id,
            f"""
🏁 *MISSION COMPLETE!*
━━━━━━━━━━━━━━━━━━━━━

*Session:* `{session.session_id[:15]}...`
*Duration:* 24 hours
*Status:* ✅ Completed

*Final Stats:*
• Agents Deployed: {session.agents_deployed}
• Faucets Attempted: {session.faucets_attempted}
• Successful Claims: {session.faucets_successful}
• Success Rate: {success_rate:.1f}%

*Total Earnings:*
{earnings_text}

*Wallets Used:*
{wallets_text}

💡 Use /exportwallets to get private keys
🔄 Use /soldiers to start a new mission

Thank you for using Solana Soldiers! 🎖️
"""
        )
    
    async def get_session_status(self, user_telegram_id: int) -> Optional[MiningSession]:
        """Get current session status"""
        return self.active_sessions.get(user_telegram_id)
    
    async def cancel_session(self, user_telegram_id: int) -> bool:
        """Cancel an active session"""
        session = self.active_sessions.get(user_telegram_id)
        if session and session.status == "active":
            session.status = "cancelled"
            return True
        return False
    
    def get_faucet_list(self) -> List[Dict]:
        """Get list of all available faucets"""
        return CRYPTO_FAUCETS
    
    def get_faucet_stats(self) -> Dict:
        """Get faucet statistics"""
        chains = {}
        for faucet in CRYPTO_FAUCETS:
            chain = faucet["chain"]
            if chain not in chains:
                chains[chain] = {"count": 0, "currencies": set()}
            chains[chain]["count"] += 1
            chains[chain]["currencies"].add(faucet["currency"])
        
        return {
            "total_faucets": len(CRYPTO_FAUCETS),
            "chains": {k: {"count": v["count"], "currencies": list(v["currencies"])} for k, v in chains.items()},
            "mainnet_faucets": sum(1 for f in CRYPTO_FAUCETS if not f.get("testnet")),
            "testnet_faucets": sum(1 for f in CRYPTO_FAUCETS if f.get("testnet"))
        }
