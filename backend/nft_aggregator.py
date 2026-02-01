"""
NFT Aggregator - Aggregates NFT data from multiple marketplaces
"""
import asyncio
import aiohttp
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class Marketplace(Enum):
    MAGIC_EDEN = "magic_eden"
    TENSOR = "tensor"
    OPENSEA = "opensea"
    BLUR = "blur"
    RARIBLE = "rarible"

@dataclass
class NFTCollection:
    name: str
    symbol: str
    marketplace: str
    chain: str
    floor_price: float
    currency: str
    volume_24h: float
    volume_7d: float
    listed_count: int
    total_supply: int
    holders: int
    royalty_pct: float
    verified: bool
    image_url: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    twitter: Optional[str] = None
    discord: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass  
class NFTItem:
    token_id: str
    collection_name: str
    name: str
    image_url: str
    marketplace: str
    chain: str
    price: float
    currency: str
    rarity_rank: Optional[int] = None
    rarity_score: Optional[float] = None
    attributes: List[Dict] = field(default_factory=list)
    last_sale_price: Optional[float] = None
    owner: Optional[str] = None
    listed_at: Optional[str] = None

@dataclass
class MarketTrend:
    chain: str
    total_volume_24h: float
    total_sales_24h: int
    avg_price: float
    trending_collections: List[str]
    top_sales: List[Dict]
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class NFTAggregator:
    """Aggregates NFT data from multiple marketplaces"""
    
    def __init__(self):
        self.collections_cache: Dict[str, NFTCollection] = {}
        self.trends_cache: Dict[str, MarketTrend] = {}
        self.last_update: Optional[datetime] = None
    
    async def get_trending_collections(self, chain: str = "solana", limit: int = 20) -> List[NFTCollection]:
        """Get trending NFT collections"""
        collections = []
        
        if chain == "solana":
            # Magic Eden API
            me_collections = await self._fetch_magic_eden_trending(limit)
            collections.extend(me_collections)
            
            # Tensor API
            tensor_collections = await self._fetch_tensor_trending(limit)
            collections.extend(tensor_collections)
        
        elif chain == "ethereum":
            # OpenSea API
            os_collections = await self._fetch_opensea_trending(limit)
            collections.extend(os_collections)
            
            # Blur API
            blur_collections = await self._fetch_blur_trending(limit)
            collections.extend(blur_collections)
        
        # Deduplicate by name
        seen = set()
        unique_collections = []
        for c in collections:
            if c.name not in seen:
                seen.add(c.name)
                unique_collections.append(c)
        
        return sorted(unique_collections, key=lambda x: x.volume_24h, reverse=True)[:limit]
    
    async def _fetch_magic_eden_trending(self, limit: int) -> List[NFTCollection]:
        """Fetch trending from Magic Eden"""
        collections = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api-mainnet.magiceden.dev/v2/collections?offset=0&limit=20",
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data[:limit]:
                            collections.append(NFTCollection(
                                name=item.get("name", "Unknown"),
                                symbol=item.get("symbol", ""),
                                marketplace="Magic Eden",
                                chain="solana",
                                floor_price=item.get("floorPrice", 0) / 1e9,  # Convert lamports to SOL
                                currency="SOL",
                                volume_24h=item.get("volumeAll", 0) / 1e9,
                                volume_7d=0,
                                listed_count=item.get("listedCount", 0),
                                total_supply=item.get("totalSupply", 0),
                                holders=item.get("uniqueHolders", 0),
                                royalty_pct=item.get("sellerFeeBasisPoints", 0) / 100,
                                verified=item.get("isVerified", False),
                                image_url=item.get("image"),
                                description=item.get("description")
                            ))
        except Exception as e:
            logger.error(f"Error fetching Magic Eden: {e}")
        
        return collections
    
    async def _fetch_tensor_trending(self, limit: int) -> List[NFTCollection]:
        """Fetch trending from Tensor"""
        collections = []
        try:
            async with aiohttp.ClientSession() as session:
                # Tensor GraphQL endpoint
                async with session.post(
                    "https://api.tensor.so/graphql",
                    json={
                        "query": """
                            query TrendingCollections($limit: Int!) {
                                trendingCollections(limit: $limit) {
                                    slug
                                    name
                                    floorPrice
                                    volume24h
                                    numListed
                                    numMints
                                }
                            }
                        """,
                        "variables": {"limit": limit}
                    },
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get("data", {}).get("trendingCollections", [])
                        for item in items:
                            collections.append(NFTCollection(
                                name=item.get("name", "Unknown"),
                                symbol=item.get("slug", ""),
                                marketplace="Tensor",
                                chain="solana",
                                floor_price=float(item.get("floorPrice", 0)) / 1e9,
                                currency="SOL",
                                volume_24h=float(item.get("volume24h", 0)) / 1e9,
                                volume_7d=0,
                                listed_count=item.get("numListed", 0),
                                total_supply=item.get("numMints", 0),
                                holders=0,
                                royalty_pct=0,
                                verified=True
                            ))
        except Exception as e:
            logger.debug(f"Error fetching Tensor: {e}")
        
        return collections
    
    async def _fetch_opensea_trending(self, limit: int) -> List[NFTCollection]:
        """Fetch trending from OpenSea"""
        collections = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.opensea.io/api/v2/collections?limit={limit}",
                    headers={"Accept": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data.get("collections", []):
                            collections.append(NFTCollection(
                                name=item.get("name", "Unknown"),
                                symbol=item.get("collection", ""),
                                marketplace="OpenSea",
                                chain="ethereum",
                                floor_price=float(item.get("stats", {}).get("floor_price", 0) or 0),
                                currency="ETH",
                                volume_24h=float(item.get("stats", {}).get("one_day_volume", 0) or 0),
                                volume_7d=float(item.get("stats", {}).get("seven_day_volume", 0) or 0),
                                listed_count=item.get("stats", {}).get("num_listings", 0) or 0,
                                total_supply=item.get("stats", {}).get("total_supply", 0) or 0,
                                holders=item.get("stats", {}).get("num_owners", 0) or 0,
                                royalty_pct=float(item.get("fees", {}).get("seller_fees", 0) or 0),
                                verified=item.get("safelist_status") == "verified",
                                image_url=item.get("image_url"),
                                description=item.get("description")
                            ))
        except Exception as e:
            logger.debug(f"Error fetching OpenSea: {e}")
        
        return collections
    
    async def _fetch_blur_trending(self, limit: int) -> List[NFTCollection]:
        """Fetch trending from Blur"""
        # Blur doesn't have a public API, return empty for now
        return []
    
    async def get_collection_details(self, collection_slug: str, chain: str = "solana") -> Optional[NFTCollection]:
        """Get detailed info about a specific collection"""
        if chain == "solana":
            return await self._get_magic_eden_collection(collection_slug)
        elif chain == "ethereum":
            return await self._get_opensea_collection(collection_slug)
        return None
    
    async def _get_magic_eden_collection(self, slug: str) -> Optional[NFTCollection]:
        """Get collection details from Magic Eden"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api-mainnet.magiceden.dev/v2/collections/{slug}",
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        item = await response.json()
                        return NFTCollection(
                            name=item.get("name", "Unknown"),
                            symbol=item.get("symbol", ""),
                            marketplace="Magic Eden",
                            chain="solana",
                            floor_price=item.get("floorPrice", 0) / 1e9,
                            currency="SOL",
                            volume_24h=item.get("volumeAll", 0) / 1e9,
                            volume_7d=0,
                            listed_count=item.get("listedCount", 0),
                            total_supply=item.get("totalSupply", 0),
                            holders=item.get("uniqueHolders", 0),
                            royalty_pct=item.get("sellerFeeBasisPoints", 0) / 100,
                            verified=item.get("isVerified", False),
                            image_url=item.get("image"),
                            description=item.get("description"),
                            website=item.get("website"),
                            twitter=item.get("twitter"),
                            discord=item.get("discord")
                        )
        except Exception as e:
            logger.error(f"Error fetching collection {slug}: {e}")
        return None
    
    async def _get_opensea_collection(self, slug: str) -> Optional[NFTCollection]:
        """Get collection details from OpenSea"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.opensea.io/api/v2/collections/{slug}",
                    headers={"Accept": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        item = await response.json()
                        return NFTCollection(
                            name=item.get("name", "Unknown"),
                            symbol=item.get("collection", ""),
                            marketplace="OpenSea",
                            chain="ethereum",
                            floor_price=float(item.get("stats", {}).get("floor_price", 0) or 0),
                            currency="ETH",
                            volume_24h=float(item.get("stats", {}).get("one_day_volume", 0) or 0),
                            volume_7d=float(item.get("stats", {}).get("seven_day_volume", 0) or 0),
                            listed_count=item.get("stats", {}).get("num_listings", 0) or 0,
                            total_supply=item.get("stats", {}).get("total_supply", 0) or 0,
                            holders=item.get("stats", {}).get("num_owners", 0) or 0,
                            royalty_pct=float(item.get("fees", {}).get("seller_fees", 0) or 0),
                            verified=item.get("safelist_status") == "verified",
                            image_url=item.get("image_url"),
                            description=item.get("description")
                        )
        except Exception as e:
            logger.error(f"Error fetching OpenSea collection {slug}: {e}")
        return None
    
    async def get_collection_items(
        self, 
        collection_slug: str, 
        chain: str = "solana",
        limit: int = 20,
        sort_by: str = "price"
    ) -> List[NFTItem]:
        """Get listed items from a collection"""
        items = []
        
        if chain == "solana":
            items = await self._get_magic_eden_listings(collection_slug, limit)
        elif chain == "ethereum":
            items = await self._get_opensea_listings(collection_slug, limit)
        
        # Sort items
        if sort_by == "price":
            items.sort(key=lambda x: x.price)
        elif sort_by == "rarity":
            items.sort(key=lambda x: x.rarity_rank or float('inf'))
        
        return items
    
    async def _get_magic_eden_listings(self, slug: str, limit: int) -> List[NFTItem]:
        """Get listings from Magic Eden"""
        items = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api-mainnet.magiceden.dev/v2/collections/{slug}/listings?limit={limit}",
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data:
                            items.append(NFTItem(
                                token_id=item.get("tokenMint", ""),
                                collection_name=slug,
                                name=item.get("extra", {}).get("name", f"#{item.get('tokenMint', '')[:8]}"),
                                image_url=item.get("extra", {}).get("img", ""),
                                marketplace="Magic Eden",
                                chain="solana",
                                price=item.get("price", 0),
                                currency="SOL",
                                rarity_rank=item.get("rarity", {}).get("rank"),
                                attributes=item.get("extra", {}).get("attributes", []),
                                owner=item.get("seller")
                            ))
        except Exception as e:
            logger.error(f"Error fetching ME listings for {slug}: {e}")
        
        return items
    
    async def _get_opensea_listings(self, slug: str, limit: int) -> List[NFTItem]:
        """Get listings from OpenSea"""
        items = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.opensea.io/api/v2/listings/collection/{slug}/all?limit={limit}",
                    headers={"Accept": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        for item in data.get("listings", []):
                            protocol_data = item.get("protocol_data", {}).get("parameters", {})
                            offer = protocol_data.get("offer", [{}])[0]
                            items.append(NFTItem(
                                token_id=offer.get("identifierOrCriteria", ""),
                                collection_name=slug,
                                name=f"#{offer.get('identifierOrCriteria', '')[:8]}",
                                image_url="",
                                marketplace="OpenSea",
                                chain="ethereum",
                                price=float(item.get("price", {}).get("current", {}).get("value", 0)) / 1e18,
                                currency="ETH",
                                owner=protocol_data.get("offerer")
                            ))
        except Exception as e:
            logger.debug(f"Error fetching OpenSea listings for {slug}: {e}")
        
        return items
    
    async def get_market_trends(self, chain: str = "solana") -> MarketTrend:
        """Get overall market trends"""
        collections = await self.get_trending_collections(chain, limit=50)
        
        total_volume = sum(c.volume_24h for c in collections)
        avg_price = sum(c.floor_price for c in collections) / len(collections) if collections else 0
        
        return MarketTrend(
            chain=chain,
            total_volume_24h=total_volume,
            total_sales_24h=0,  # Would need additional API calls
            avg_price=avg_price,
            trending_collections=[c.name for c in collections[:10]],
            top_sales=[]
        )
    
    async def search_collections(self, query: str, chain: str = "solana") -> List[NFTCollection]:
        """Search for collections by name"""
        all_collections = await self.get_trending_collections(chain, limit=100)
        query_lower = query.lower()
        return [c for c in all_collections if query_lower in c.name.lower()]
    
    def format_collection_summary(self, collection: NFTCollection) -> str:
        """Format collection data for display"""
        verified = "✅" if collection.verified else "❌"
        return f"""
*{collection.name}* {verified}
━━━━━━━━━━━━━━━━━━━━━
📊 *Market Data:*
• Floor: {collection.floor_price:.4f} {collection.currency}
• Volume 24h: {collection.volume_24h:.2f} {collection.currency}
• Listed: {collection.listed_count:,}
• Supply: {collection.total_supply:,}
• Holders: {collection.holders:,}
• Royalty: {collection.royalty_pct:.1f}%

🏪 Marketplace: {collection.marketplace}
⛓️ Chain: {collection.chain.upper()}
"""

    def format_item_summary(self, item: NFTItem) -> str:
        """Format NFT item for display"""
        rarity = f"Rank #{item.rarity_rank}" if item.rarity_rank else "N/A"
        return f"""
*{item.name}*
• Price: {item.price:.4f} {item.currency}
• Rarity: {rarity}
• Marketplace: {item.marketplace}
"""
