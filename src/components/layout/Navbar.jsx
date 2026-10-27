import React, { useState, useRef, useEffect } from 'react';
import { fetchLeaderboard } from '../../services/api';

export default function Navbar({
  selectedProduct,
  onSelectProduct,
  currentUser,
  onSwitchUser,
  onOpenOnboarding,
  includeQuarantined,
  onToggleQuarantined,
  onNavigateLanding,
}) {
  const [products, setProducts] = useState([
    { id: 'prod_001', name: 'Voyage Horizon ANC', health_score: 84 },
    { id: 'prod_002', name: 'Voyage StreamCast Pro', health_score: 88 },
    { id: 'prod_003', name: 'Voyage Apex Wireless', health_score: 86 },
    { id: 'prod_004', name: 'Voyage UltraVision 27"', health_score: 82 },
  ]);

  useEffect(() => {
    let isMounted = true;
    fetchLeaderboard().then((res) => {
      if (isMounted && Array.isArray(res) && res.length > 0) {
        setProducts(res.map((p) => ({ id: p.product_id, name: p.name || p.product_id, health_score: p.health_score })));
      }
    });
    return () => { isMounted = false; };
  }, []);

  const currentProduct = products.find((p) => p.id === selectedProduct) || products[0];
  const [isStorefrontOpen, setIsStorefrontOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const dropdownRef = useRef(null);
  const userMenuRef = useRef(null);

  const storefronts = [
    {
      id: 'amazon',
      name: 'Amazon India',
      url: '/simulation/amazon.html',
      badge: 'Marketplace',
      color: 'text-amber-300 bg-amber-500/10 border-amber-500/20',
      desc: 'Simulate Amazon electronics storefront & user reviews',
    },
    {
      id: 'flipkart',
      name: 'Flipkart',
      url: '/simulation/flipkart.html',
      badge: 'Marketplace',
      color: 'text-sky-300 bg-sky-500/10 border-sky-500/20',
      desc: 'Flipkart product page with verified buyer reviews',
    },
    {
      id: 'jiomart',
      name: 'JioMart',
      url: '/simulation/jiomart.html',
      badge: 'Retail',
      color: 'text-rose-300 bg-rose-500/10 border-rose-500/20',
      desc: 'JioMart catalog reviews & delivery ratings',
    },
    {
      id: 'brand',
      name: 'Brand Direct Store',
      url: '/simulation/brand.html',
      badge: 'Direct (D2C)',
      color: 'text-teal-300 bg-teal-500/10 border-teal-500/20',
      desc: 'Official direct-to-consumer store & warranty feedback',
    },
    {
      id: 'charts',
      name: 'Live Dashboard Simulation',
      url: '/simulation/dashboard-charts.html',
      badge: 'Diagnostics',
      color: 'text-purple-300 bg-purple-500/10 border-purple-500/20',
      desc: 'Simulation chart telemetry and socket events',
    },
  ];

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsStorefrontOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setIsUserMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="h-16 border-b border-zinc-800 bg-[#18191f] px-5 flex items-center justify-between sticky top-0 z-40 select-none">
      {/* Brand & Product Selector */}
      <div className="flex items-center gap-4">
        {/* PRISM Brand */}
        <div className="flex items-center gap-2.5 cursor-pointer group" onClick={onNavigateLanding} title="Go to Landing Page">
          <div className="w-7 h-7 rounded-md bg-white text-zinc-950 font-extrabold flex items-center justify-center text-xs tracking-tighter shadow-sm group-hover:scale-105 transition-transform">
            P
          </div>
          <div>
            <div className="font-extrabold text-sm tracking-[0.2em] text-white leading-none">PRISM</div>
            <div className="text-[9px] tracking-wider text-zinc-400 uppercase mt-0.5">Intelligence</div>
          </div>
        </div>

        <div className="h-4 w-[1px] bg-zinc-800 hidden sm:block" />

        {/* Product Dropdown */}
        <div className="hidden sm:flex items-center gap-2">
          <span className="text-[11px] text-zinc-400 font-medium">Target:</span>
          <select
            value={selectedProduct}
            onChange={(e) => onSelectProduct(e.target.value)}
            className="bg-[#22242d] border border-zinc-700/60 text-xs text-white rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-zinc-400 transition-colors font-medium cursor-pointer"
          >
            {products.map((prod) => (
              <option key={prod.id} value={prod.id}>
                {prod.name} (Health: {prod.health_score || '—'})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Trust & Quarantine Audit Metric */}
      <div className="hidden xl:flex items-center gap-3.5 px-3.5 py-1 rounded-full bg-[#22242d] border border-zinc-700/60 text-xs">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-zinc-300" />
          <span className="text-zinc-400">Product:</span>
          <span className="font-mono font-medium text-white">{currentProduct?.id}</span>
        </div>
        <div className="text-zinc-700">|</div>
        <div className="flex items-center gap-2">
          <span className="text-zinc-400">Health Score:</span>
          <span className="font-mono font-medium text-zinc-200">{currentProduct?.health_score || 50} / 100</span>
        </div>
        <div className="text-zinc-700">|</div>
        <button
          onClick={onToggleQuarantined}
          title="Toggle between clean audited reviews and quarantined reviews"
          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide transition-all ${
            includeQuarantined
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              : 'bg-white/5 text-zinc-300 hover:text-white border border-white/10'
          }`}
        >
          {includeQuarantined ? 'Quarantined Included' : 'Clean Only (Audited)'}
        </button>
      </div>

      {/* Interactive Actions */}
      <div className="flex items-center gap-3">

        {/* Storefronts Dropdown Menu */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setIsStorefrontOpen(!isStorefrontOpen)}
            className={`text-xs px-3 py-1.5 rounded-lg border font-semibold flex items-center gap-1.5 transition-all ${
              isStorefrontOpen
                ? 'bg-white text-zinc-950 border-white shadow-sm'
                : 'bg-[#22242d] hover:bg-zinc-800 border-zinc-700/60 text-zinc-200'
            }`}
            title="Choose a simulated website to open"
          >
            <span>Storefronts</span>
            <svg className={`w-3 h-3 text-zinc-400 transition-transform duration-200 ${isStorefrontOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {isStorefrontOpen && (
            <div className="absolute right-0 mt-2 w-72 rounded-xl bg-[#22242d] border border-zinc-700/70 shadow-2xl p-2 z-50">
              <div className="px-2 py-1.5 text-[10px] font-bold uppercase tracking-wider text-zinc-400 border-b border-zinc-800 mb-1">
                Select Simulation Website
              </div>
              <div className="space-y-1">
                {storefronts.map((site) => (
                  <a
                    key={site.id}
                    href={site.url}
                    target="_blank"
                    rel="noreferrer"
                    onClick={() => setIsStorefrontOpen(false)}
                    className="flex items-start justify-between p-2 rounded-lg hover:bg-zinc-800 transition-colors group cursor-pointer"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-white group-hover:text-zinc-200 transition-colors">
                          {site.name}
                        </span>
                        <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded border ${site.color}`}>
                          {site.badge}
                        </span>
                      </div>
                      <p className="text-[10px] text-zinc-400 truncate mt-0.5">
                        {site.desc}
                      </p>
                    </div>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Authenticated User Profile Pill */}
        {currentUser && (
          <div className="relative" ref={userMenuRef}>
            <button
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              className="flex items-center gap-2 pl-2 pr-2.5 py-1 rounded-lg bg-[#22242d] hover:bg-zinc-800 border border-zinc-700/60 text-xs text-zinc-200 transition-colors cursor-pointer"
              title="Current User Profile"
            >
              <div className="w-5 h-5 rounded-full bg-zinc-800 text-zinc-100 flex items-center justify-center font-bold text-[10px] border border-zinc-600">
                {currentUser.name ? currentUser.name[0] : 'U'}
              </div>
              <span className="font-medium max-w-[100px] truncate hidden md:inline">
                {currentUser.name.split(' ')[0]}
              </span>
              <svg className={`w-3 h-3 text-zinc-400 transition-transform duration-200 ${isUserMenuOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {isUserMenuOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-xl bg-[#22242d] border border-zinc-700/70 shadow-2xl p-3 z-50">
                <div className="flex items-center gap-2.5 pb-2.5 border-b border-zinc-800 mb-2.5">
                  <div className="w-8 h-8 rounded-full bg-zinc-800 text-zinc-100 flex items-center justify-center font-bold text-xs border border-zinc-600">
                    {currentUser.name ? currentUser.name[0] : 'U'}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="font-bold text-xs text-white truncate">{currentUser.name}</div>
                    <div className="text-[10px] text-zinc-400 truncate">{currentUser.email}</div>
                  </div>
                </div>

                <div className="space-y-1 text-[10px] text-zinc-400 mb-3 font-mono">
                  <div className="flex justify-between">
                    <span>Badge ID:</span>
                    <span className="text-white font-semibold">{currentUser.empId || 'PRISM-EMP'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Department:</span>
                    <span className="text-zinc-200 font-semibold">{currentUser.roleData?.badge || currentUser.role}</span>
                  </div>
                </div>

                <button
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    onOpenOnboarding && onOpenOnboarding();
                  }}
                  className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-semibold text-zinc-200 hover:bg-zinc-800 transition-colors flex items-center justify-between cursor-pointer mb-1 border border-zinc-700"
                >
                  <span>Personalize Views (F27)</span>
                </button>

                <button
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    onSwitchUser();
                  }}
                  className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-semibold text-rose-300 hover:bg-rose-500/10 transition-colors flex items-center justify-between cursor-pointer"
                >
                  <span>Sign Out (SSO Gateway)</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* Landing Page Button */}
        <button
          onClick={onNavigateLanding}
          className="text-xs px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white font-semibold transition-colors"
          title="Return to Landing Page"
        >
          Landing
        </button>
      </div>
    </header>
  );
}
