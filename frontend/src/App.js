import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { motion } from "framer-motion";
import { 
  Activity, 
  Wallet, 
  TrendingUp, 
  Users, 
  Shield, 
  Zap, 
  ExternalLink,
  Copy,
  CheckCircle,
  XCircle,
  Clock,
  DollarSign,
  BarChart3,
  RefreshCw,
  AlertTriangle,
  Target,
  Flame,
  Eye
} from "lucide-react";
import { Toaster, toast } from "sonner";
import "@/App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Whale wallets to display
const WHALE_WALLETS = [
  "74YhGgHA3x1jcL2TchwChDbRVVXvzSxNbYM6ytCukauM",
  "2KUCqnm5c49wqG9cUyDiv9fVs12EMmNtBsrKpVZzLovd",
  "EthJwgUrj8drTsUZxFt13uBpQeMv3E1ceDyGAseNaxeh",
  "CkVqgWTBdZSbiaycU5K1M3JttKdAyjTwRbfZXoFugo65",
  "7NTV2q79Ee4gqTH1KS52u14BA7GDvDUZmkzd7xE3Kxci"
];

// Payment addresses
const PAYMENT_ADDRESSES = {
  SOL: "TXFm5oQQ4Qp51tMkPgdqSESYdQaN6hqQkpoZidWMdSy",
  ETH: "0x125FeD6C4A538aaD4108cE5D598628DC42635Fe9",
  BTC: "bc1p3red8wgfa9k2qyhxxj9vpnehvy29ld63lg5t6kfvrcy6lz7l9mhspyjk3k"
};

// Stat Card Component
const StatCard = ({ icon: Icon, label, value, color, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay, duration: 0.5 }}
    className="glass-card p-6"
    data-testid={`stat-card-${label.toLowerCase().replace(/\s+/g, '-')}`}
  >
    <div className="flex items-center gap-4">
      <div className={`p-3 rounded-sm ${color}`}>
        <Icon className="w-6 h-6" />
      </div>
      <div>
        <p className="text-gray-400 text-sm font-rajdhani uppercase tracking-wider">{label}</p>
        <p className="text-2xl font-unbounded font-bold text-white">{value}</p>
      </div>
    </div>
  </motion.div>
);

// Whale Card Component
const WhaleCard = ({ address, index }) => {
  const [copied, setCopied] = useState(false);
  
  const copyAddress = () => {
    navigator.clipboard.writeText(address);
    setCopied(true);
    toast.success("Address copied!");
    setTimeout(() => setCopied(false), 2000);
  };
  
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1 }}
      className="glass-card p-4 flex items-center justify-between group hover:border-[#14F195]/30 transition-all"
      data-testid={`whale-card-${index}`}
    >
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-sm bg-gradient-to-r from-[#9945FF] to-[#14F195] flex items-center justify-center text-black font-bold text-sm">
          {index + 1}
        </div>
        <code className="text-gray-300 text-sm font-mono">
          {address.slice(0, 8)}...{address.slice(-8)}
        </code>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={copyAddress}
          className="p-2 hover:bg-white/10 rounded-sm transition-all"
          data-testid={`copy-whale-${index}`}
        >
          {copied ? <CheckCircle className="w-4 h-4 text-[#14F195]" /> : <Copy className="w-4 h-4 text-gray-400" />}
        </button>
        <a
          href={`https://solscan.io/account/${address}`}
          target="_blank"
          rel="noopener noreferrer"
          className="p-2 hover:bg-white/10 rounded-sm transition-all"
          data-testid={`view-whale-${index}`}
        >
          <ExternalLink className="w-4 h-4 text-gray-400" />
        </a>
      </div>
    </motion.div>
  );
};

// Landing Page
const LandingPage = () => {
  const features = [
    { icon: Activity, title: "Real-Time Tracking", desc: "Monitor whale wallets 24/7 for trading opportunities" },
    { icon: Zap, title: "Lightning Fast", desc: "Execute trades in under 2 minutes" },
    { icon: Shield, title: "Anti-Rug Protection", desc: "Built-in safety measures to protect your funds" },
    { icon: TrendingUp, title: "$2 Profit Target", desc: "Consistent small profits, minimal risk" }
  ];
  
  return (
    <div className="min-h-screen bg-[#050505] relative overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#9945FF]/10 via-transparent to-[#14F195]/10 pointer-events-none" />
      
      {/* Hero Section */}
      <div className="relative z-10 px-6 py-12 md:px-12 lg:px-24">
        <nav className="flex items-center justify-between mb-16">
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-3"
          >
            <div className="w-10 h-10 gradient-primary rounded-sm flex items-center justify-center">
              <Shield className="w-6 h-6 text-black" />
            </div>
            <span className="font-unbounded font-bold text-xl text-white">SOLANA SOLDIER</span>
          </motion.div>
          
          <motion.a
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            href="https://t.me/SolanaSoldierBot"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary px-6 py-3 rounded-sm flex items-center gap-2"
            data-testid="launch-bot-btn"
          >
            <Zap className="w-4 h-4" />
            Launch Bot
          </motion.a>
        </nav>
        
        {/* Hero Content */}
        <div className="grid md:grid-cols-12 gap-8 mb-16">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="md:col-span-7 space-y-6"
          >
            <h1 className="font-unbounded font-black text-4xl md:text-5xl lg:text-6xl text-white uppercase tracking-tighter leading-tight">
              Automated <span className="text-gradient">Solana</span> Arbitrage Trading
            </h1>
            <p className="text-gray-400 text-lg md:text-xl font-rajdhani max-w-xl">
              Track whale wallets, find new tokens, and execute profitable trades automatically. 
              100+ trades per day with anti-rug protection.
            </p>
            <div className="flex flex-wrap gap-4 pt-4">
              <a
                href="https://t.me/SolanaSoldierBot"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary px-8 py-4 rounded-sm flex items-center gap-2 text-lg"
                data-testid="get-started-btn"
              >
                Get Started
                <Zap className="w-5 h-5" />
              </a>
              <a
                href="#features"
                className="btn-secondary px-8 py-4 rounded-sm"
                data-testid="learn-more-btn"
              >
                Learn More
              </a>
            </div>
          </motion.div>
          
          {/* Stats Panel */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="md:col-span-5 glass-card p-6 animate-pulse-glow"
          >
            <h3 className="font-unbounded font-bold text-lg mb-4 text-white">Live Stats</h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center border-b border-white/10 pb-3">
                <span className="text-gray-400">Tracked Whales</span>
                <span className="font-mono text-[#14F195] text-xl">{WHALE_WALLETS.length}+</span>
              </div>
              <div className="flex justify-between items-center border-b border-white/10 pb-3">
                <span className="text-gray-400">Daily Trades</span>
                <span className="font-mono text-[#14F195] text-xl">100+</span>
              </div>
              <div className="flex justify-between items-center border-b border-white/10 pb-3">
                <span className="text-gray-400">Profit Target</span>
                <span className="font-mono text-[#14F195] text-xl">$2/trade</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Trade Time</span>
                <span className="font-mono text-[#14F195] text-xl">&lt;2 min</span>
              </div>
            </div>
          </motion.div>
        </div>
        
        {/* Features */}
        <div id="features" className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * index }}
              className="glass-card p-6 hover:border-[#9945FF]/30 transition-all"
              data-testid={`feature-${index}`}
            >
              <feature.icon className="w-10 h-10 text-[#9945FF] mb-4" />
              <h3 className="font-unbounded font-bold text-white mb-2">{feature.title}</h3>
              <p className="text-gray-400 text-sm">{feature.desc}</p>
            </motion.div>
          ))}
        </div>
        
        {/* Whale Wallets */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="mb-16"
        >
          <h2 className="font-unbounded font-bold text-2xl text-white mb-6 flex items-center gap-3">
            <Activity className="w-6 h-6 text-[#14F195]" />
            Tracked Whale Wallets
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            {WHALE_WALLETS.map((wallet, index) => (
              <WhaleCard key={wallet} address={wallet} index={index} />
            ))}
          </div>
        </motion.div>
        
        {/* Pricing */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="glass-card p-8 max-w-2xl mx-auto text-center"
          data-testid="pricing-section"
        >
          <h2 className="font-unbounded font-bold text-3xl text-white mb-4">Daily Access</h2>
          <div className="text-5xl font-unbounded font-black text-gradient mb-6">£100</div>
          <p className="text-gray-400 mb-8">Per day • Unlimited trades • Full whale tracking</p>
          
          <div className="space-y-4">
            <p className="text-sm text-gray-400 uppercase tracking-wider">Pay with</p>
            <div className="grid grid-cols-3 gap-4">
              <div className="glass-card p-4 text-center hover:border-[#9945FF]/50 transition-all cursor-pointer" data-testid="pay-sol">
                <div className="text-2xl mb-2">🟣</div>
                <div className="font-bold text-white">SOL</div>
              </div>
              <div className="glass-card p-4 text-center hover:border-[#00F0FF]/50 transition-all cursor-pointer" data-testid="pay-eth">
                <div className="text-2xl mb-2">🔵</div>
                <div className="font-bold text-white">ETH</div>
              </div>
              <div className="glass-card p-4 text-center hover:border-[#FF9500]/50 transition-all cursor-pointer" data-testid="pay-btc">
                <div className="text-2xl mb-2">🟠</div>
                <div className="font-bold text-white">BTC</div>
              </div>
            </div>
          </div>
          
          <div className="mt-8">
            <a
              href="https://t.me/SolanaSoldierBot"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary px-8 py-4 rounded-sm inline-flex items-center gap-2"
              data-testid="start-trading-btn"
            >
              Start Trading Now
              <Zap className="w-5 h-5" />
            </a>
          </div>
          
          <p className="mt-4 text-sm text-gray-500">
            Contact: <a href="https://t.me/memecorpofficial" className="text-[#14F195] hover:underline">@memecorpofficial</a>
          </p>
        </motion.div>
        
        {/* Footer */}
        <footer className="mt-16 text-center text-gray-500 text-sm">
          <p>&copy; 2026 Solana Soldier. All rights reserved.</p>
        </footer>
      </div>
    </div>
  );
};

// Dashboard Page
const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [trades, setTrades] = useState([]);
  const [payments, setPayments] = useState([]);
  const [solPrice, setSolPrice] = useState(0);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [trendingTokens, setTrendingTokens] = useState([]);
  const [whaleActivities, setWhaleActivities] = useState([]);
  const [tradingStats, setTradingStats] = useState(null);
  const [rugCheckAddress, setRugCheckAddress] = useState("");
  const [rugCheckResult, setRugCheckResult] = useState(null);
  const [checkingRug, setCheckingRug] = useState(false);
  
  const fetchData = async () => {
    try {
      const [statsRes, usersRes, tradesRes, paymentsRes, priceRes, trendingRes, whaleRes, tradingRes] = await Promise.all([
        axios.get(`${API}/stats`),
        axios.get(`${API}/users`),
        axios.get(`${API}/trades`),
        axios.get(`${API}/payments`),
        axios.get(`${API}/sol-price`),
        axios.get(`${API}/trending-tokens`).catch(() => ({ data: { tokens: [] } })),
        axios.get(`${API}/whale-activities`).catch(() => ({ data: { activities: [] } })),
        axios.get(`${API}/trading-stats`).catch(() => ({ data: {} }))
      ]);
      
      setStats(statsRes.data);
      setUsers(usersRes.data.users || []);
      setTrades(tradesRes.data.trades || []);
      setPayments(paymentsRes.data.payments || []);
      setSolPrice(priceRes.data.price_usd || 0);
      setTrendingTokens(trendingRes.data.tokens || []);
      setWhaleActivities(whaleRes.data.activities || []);
      setTradingStats(tradingRes.data);
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("Failed to fetch data");
    } finally {
      setLoading(false);
    }
  };
  
  const performRugCheck = async () => {
    if (!rugCheckAddress) return;
    setCheckingRug(true);
    try {
      const res = await axios.post(`${API}/rugcheck/${rugCheckAddress}`);
      setRugCheckResult(res.data);
      toast.success("Rug check complete!");
    } catch (error) {
      toast.error("Rug check failed");
    } finally {
      setCheckingRug(false);
    }
  };
  
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);
  
  if (loading) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 text-[#9945FF] animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading dashboard...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-[#050505] p-6" data-testid="dashboard">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 gradient-primary rounded-sm flex items-center justify-center">
            <Shield className="w-6 h-6 text-black" />
          </div>
          <span className="font-unbounded font-bold text-xl text-white">SOLDIER DASHBOARD</span>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="glass-card px-4 py-2 flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-[#14F195]" />
            <span className="font-mono text-white">SOL: ${solPrice.toFixed(2)}</span>
          </div>
          <button
            onClick={fetchData}
            className="p-2 glass-card hover:border-[#9945FF]/50 transition-all"
            data-testid="refresh-btn"
          >
            <RefreshCw className="w-5 h-5 text-gray-400" />
          </button>
        </div>
      </div>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <StatCard
          icon={Users}
          label="Total Users"
          value={stats?.total_users || 0}
          color="bg-[#9945FF]/20 text-[#9945FF]"
          delay={0}
        />
        <StatCard
          icon={Wallet}
          label="Active Wallets"
          value={stats?.active_wallets || 0}
          color="bg-[#14F195]/20 text-[#14F195]"
          delay={0.1}
        />
        <StatCard
          icon={BarChart3}
          label="Total Trades"
          value={stats?.total_trades || 0}
          color="bg-[#00F0FF]/20 text-[#00F0FF]"
          delay={0.2}
        />
        <StatCard
          icon={TrendingUp}
          label="Total Profit"
          value={`$${(stats?.total_profit_usd || 0).toFixed(2)}`}
          color="bg-[#FF9500]/20 text-[#FF9500]"
          delay={0.3}
        />
        <StatCard
          icon={Eye}
          label="Whale Alerts"
          value={stats?.whale_activities_today || 0}
          color="bg-[#FF3B30]/20 text-[#FF3B30]"
          delay={0.4}
        />
      </div>
      
      {/* Tabs */}
      <div className="flex gap-4 mb-6 border-b border-white/10 pb-4 overflow-x-auto">
        {["overview", "trending", "rugcheck", "whales", "trades", "users", "payments"].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 font-rajdhani font-semibold uppercase tracking-wider transition-all whitespace-nowrap ${
              activeTab === tab
                ? "text-[#14F195] border-b-2 border-[#14F195]"
                : "text-gray-400 hover:text-white"
            }`}
            data-testid={`tab-${tab}`}
          >
            {tab}
          </button>
        ))}
      </div>
      
      {/* Tab Content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        {activeTab === "overview" && (
          <div className="grid md:grid-cols-2 gap-6">
            {/* Whale Wallets */}
            <div className="glass-card p-6">
              <h3 className="font-unbounded font-bold text-lg mb-4 text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-[#14F195]" />
                Tracked Whales
              </h3>
              <div className="space-y-3">
                {WHALE_WALLETS.slice(0, 5).map((wallet, index) => (
                  <div key={wallet} className="flex items-center justify-between p-3 bg-white/5 rounded-sm">
                    <code className="text-sm text-gray-300">{wallet.slice(0, 12)}...</code>
                    <a
                      href={`https://solscan.io/account/${wallet}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#14F195] hover:underline text-sm"
                    >
                      View
                    </a>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Recent Activity */}
            <div className="glass-card p-6">
              <h3 className="font-unbounded font-bold text-lg mb-4 text-white flex items-center gap-2">
                <Clock className="w-5 h-5 text-[#9945FF]" />
                Recent Activity
              </h3>
              {trades.length > 0 ? (
                <div className="space-y-3">
                  {trades.slice(0, 5).map((trade, index) => (
                    <div key={trade.id} className="flex items-center justify-between p-3 bg-white/5 rounded-sm">
                      <div className="flex items-center gap-2">
                        {trade.trade_type === "BUY" ? (
                          <TrendingUp className="w-4 h-4 text-[#14F195]" />
                        ) : (
                          <TrendingUp className="w-4 h-4 text-red-500 transform rotate-180" />
                        )}
                        <span className="text-sm text-gray-300">{trade.trade_type}</span>
                      </div>
                      <span className={`text-sm ${trade.status === "COMPLETED" ? "text-[#14F195]" : "text-yellow-500"}`}>
                        {trade.status}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">No trades yet</p>
              )}
            </div>
          </div>
        )}
        
        {activeTab === "users" && (
          <div className="glass-card overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left p-4 text-xs uppercase tracking-wider text-gray-500">User</th>
                  <th className="text-left p-4 text-xs uppercase tracking-wider text-gray-500">Telegram ID</th>
                  <th className="text-left p-4 text-xs uppercase tracking-wider text-gray-500">Credits</th>
                  <th className="text-left p-4 text-xs uppercase tracking-wider text-gray-500">Created</th>
                </tr>
              </thead>
              <tbody>
                {users.length > 0 ? (
                  users.map((user) => (
                    <tr key={user.id} className="border-b border-white/5 hover:bg-white/5">
                      <td className="p-4 text-white font-mono">@{user.username || "Unknown"}</td>
                      <td className="p-4 text-gray-400 font-mono">{user.telegram_id}</td>
                      <td className="p-4 text-[#14F195] font-mono">{user.credits?.toFixed(2) || "0.00"}</td>
                      <td className="p-4 text-gray-500 text-sm">{new Date(user.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="4" className="p-8 text-center text-gray-500">No users yet</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        
        {activeTab === "trades" && (
          <div className="glass-card overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left p-4 text-xs uppercase tracking-wider text-gray-500">Type</th>
                  <th className="text-left p-4 text-xs uppercase tracking-wider text-gray-500">Amount</th>
                  <th className="text-left p-4 text-xs uppercase tracking-wider text-gray-500">Profit</th>
                  <th className="text-left p-4 text-xs uppercase tracking-wider text-gray-500">Status</th>
                  <th className="text-left p-4 text-xs uppercase tracking-wider text-gray-500">Date</th>
                </tr>
              </thead>
              <tbody>
                {trades.length > 0 ? (
                  trades.map((trade) => (
                    <tr key={trade.id} className="border-b border-white/5 hover:bg-white/5">
                      <td className="p-4">
                        <span className={`px-2 py-1 rounded-sm text-xs font-bold ${
                          trade.trade_type === "BUY" ? "bg-[#14F195]/20 text-[#14F195]" : "bg-red-500/20 text-red-500"
                        }`}>
                          {trade.trade_type}
                        </span>
                      </td>
                      <td className="p-4 text-white font-mono">{trade.amount_sol?.toFixed(4)} SOL</td>
                      <td className="p-4 text-[#14F195] font-mono">${trade.profit_usd?.toFixed(2) || "0.00"}</td>
                      <td className="p-4">
                        <span className={`flex items-center gap-1 ${
                          trade.status === "COMPLETED" ? "text-[#14F195]" : 
                          trade.status === "FAILED" ? "text-red-500" : "text-yellow-500"
                        }`}>
                          {trade.status === "COMPLETED" ? <CheckCircle className="w-4 h-4" /> : 
                           trade.status === "FAILED" ? <XCircle className="w-4 h-4" /> : 
                           <Clock className="w-4 h-4" />}
                          {trade.status}
                        </span>
                      </td>
                      <td className="p-4 text-gray-500 text-sm">{new Date(trade.created_at).toLocaleString()}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="5" className="p-8 text-center text-gray-500">No trades yet</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        
        {activeTab === "payments" && (
          <div className="glass-card overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left p-4 text-xs uppercase tracking-wider text-gray-500">User ID</th>
                  <th className="text-left p-4 text-xs uppercase tracking-wider text-gray-500">Amount</th>
                  <th className="text-left p-4 text-xs uppercase tracking-wider text-gray-500">Crypto</th>
                  <th className="text-left p-4 text-xs uppercase tracking-wider text-gray-500">Status</th>
                  <th className="text-left p-4 text-xs uppercase tracking-wider text-gray-500">Date</th>
                </tr>
              </thead>
              <tbody>
                {payments.length > 0 ? (
                  payments.map((payment) => (
                    <tr key={payment.id} className="border-b border-white/5 hover:bg-white/5">
                      <td className="p-4 text-white font-mono">{payment.user_telegram_id}</td>
                      <td className="p-4 text-[#14F195] font-mono">£{payment.amount_gbp}</td>
                      <td className="p-4 text-gray-400">{payment.crypto_type}</td>
                      <td className="p-4">
                        <span className={`px-2 py-1 rounded-sm text-xs font-bold ${
                          payment.status === "COMPLETED" ? "bg-[#14F195]/20 text-[#14F195]" : 
                          "bg-yellow-500/20 text-yellow-500"
                        }`}>
                          {payment.status}
                        </span>
                      </td>
                      <td className="p-4 text-gray-500 text-sm">{new Date(payment.created_at).toLocaleString()}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="5" className="p-8 text-center text-gray-500">No payments yet</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <Toaster 
        position="top-right" 
        theme="dark"
        toastOptions={{
          style: {
            background: '#0A0A0A',
            border: '1px solid rgba(255,255,255,0.1)',
            color: '#fff'
          }
        }}
      />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
