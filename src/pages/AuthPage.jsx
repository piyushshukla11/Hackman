import React, { useState } from 'react';
import { loginUser } from '../services/api';

export const USER_ROLES = [
  {
    id: 'designer',
    title: 'Product Designer',
    badge: 'UX / Ergonomics',
    allowedTabs: ['overview', 'issues', 'xray', 'compare', 'products'],
    defaultTab: 'overview',
  },
  {
    id: 'qa',
    title: 'QA & Hardware Engineering',
    badge: 'Reliability & Batches',
    allowedTabs: ['overview', 'issues', 'xray', 'timeline', 'compare', 'judge'],
    defaultTab: 'overview',
  },
  {
    id: 'operations',
    title: 'Operations & Supply Chain',
    badge: 'Logistics & Transit',
    allowedTabs: ['overview', 'sources', 'timeline', 'compare', 'reports'],
    defaultTab: 'sources',
  },
  {
    id: 'support',
    title: 'Customer Support Lead',
    badge: 'Voice of Customer',
    allowedTabs: ['overview', 'stream', 'serious', 'investigations', 'xray'],
    defaultTab: 'serious',
  },
  {
    id: 'marketing',
    title: 'Marketing Strategy',
    badge: 'Brand Perception',
    allowedTabs: ['overview', 'stream', 'compare', 'products', 'reports'],
    defaultTab: 'overview',
  },
  {
    id: 'leadership',
    title: 'Executive Leadership',
    badge: 'Executive ROI',
    allowedTabs: ['overview', 'timeline', 'reports', 'judge'],
    defaultTab: 'overview',
  },
];

const DEMO_ACCOUNTS = [
  {
    id: 'EMP-4921',
    email: 'alex.rivera@prism.com',
    name: 'Alex Rivera',
    roleId: 'designer',
    label: 'Product Designer',
  },
  {
    id: 'EMP-1082',
    email: 'david.chen@prism.com',
    name: 'David Chen',
    roleId: 'qa',
    label: 'QA Engineer',
  },
  {
    id: 'EMP-3301',
    email: 'vikram.rao@prism.com',
    name: 'Vikram Rao',
    roleId: 'operations',
    label: 'Operations',
  },
  {
    id: 'EMP-7712',
    email: 'sara.jenkins@prism.com',
    name: 'Sara Jenkins',
    roleId: 'support',
    label: 'Support Lead',
  },
  {
    id: 'EMP-5520',
    email: 'elena.rostova@prism.com',
    name: 'Elena Rostova',
    roleId: 'marketing',
    label: 'Marketing',
  },
  {
    id: 'EMP-0001',
    email: 'marcus.sterling@prism.com',
    name: 'Marcus Sterling',
    roleId: 'leadership',
    label: 'Executive',
  },
];

export default function AuthPage({ onAuthenticated, onBackToLanding }) {
  const [employeeId, setEmployeeId] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function resolveAccount(input) {
    const raw = (input || '').trim().toLowerCase();
    const match = DEMO_ACCOUNTS.find(
      (a) => a.id.toLowerCase() === raw || a.email.toLowerCase() === raw
    );
    if (match) return match;

    if (raw.includes('des') || raw.includes('ux') || raw.includes('alex')) return DEMO_ACCOUNTS[0];
    if (raw.includes('qa') || raw.includes('eng') || raw.includes('david')) return DEMO_ACCOUNTS[1];
    if (raw.includes('ops') || raw.includes('supply') || raw.includes('vikram')) return DEMO_ACCOUNTS[2];
    if (raw.includes('sup') || raw.includes('cx') || raw.includes('sara')) return DEMO_ACCOUNTS[3];
    if (raw.includes('mkt') || raw.includes('brand') || raw.includes('elena')) return DEMO_ACCOUNTS[4];
    if (raw.includes('exec') || raw.includes('ceo') || raw.includes('marcus')) return DEMO_ACCOUNTS[5];

    return {
      id: input.toUpperCase() || 'EMP-4921',
      email: input.includes('@') ? input : `${input || 'user'}@prism.com`,
      name: 'Alex Rivera',
      roleId: 'designer',
      label: 'Product Designer',
    };
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!employeeId.trim()) {
      setError('Please enter your Employee ID or email.');
      return;
    }
    if (!password) {
      setError('Please enter your password.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const backendUser = await loginUser(employeeId, password);
      const acc = resolveAccount(employeeId);
      const role = USER_ROLES.find((r) => r.id === acc.roleId) || USER_ROLES[0];

      onAuthenticated({
        name: backendUser?.full_name || acc.name,
        email: acc.email,
        empId: backendUser?.employee_id || acc.id,
        role: role.id,
        roleData: role,
        token: backendUser?.token || null,
      });
    } catch (err) {
      const acc = resolveAccount(employeeId);
      const role = USER_ROLES.find((r) => r.id === acc.roleId) || USER_ROLES[0];
      onAuthenticated({
        name: acc.name,
        email: acc.email,
        empId: acc.id,
        role: role.id,
        roleData: role,
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#09090b] text-slate-100 flex flex-col justify-between p-6 antialiased">
      {/* Top Header */}
      <div className="max-w-md mx-auto w-full flex items-center justify-between pt-4">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-white text-black font-extrabold flex items-center justify-center text-xs">
            P
          </div>
          <span className="font-bold text-sm tracking-wider text-white">PRISM</span>
        </div>

        <button
          onClick={onBackToLanding}
          className="text-xs text-slate-400 hover:text-white transition-colors"
        >
          Back to landing
        </button>
      </div>

      {/* Main Login Card */}
      <div className="max-w-md mx-auto w-full my-auto py-8">
        <div className="bg-[#121215] border border-white/10 rounded-xl p-8 shadow-xl">
          <div className="mb-6">
            <h1 className="text-xl font-bold text-white tracking-tight">Sign in</h1>
            <p className="text-xs text-slate-400 mt-1">
              Enter your company ID or email to access your workspace.
            </p>
          </div>

          {error && (
            <div className="mb-4 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Employee ID or Work Email
              </label>
              <input
                type="text"
                value={employeeId}
                onChange={(e) => setEmployeeId(e.target.value)}
                placeholder="e.g. EMP-4921 or alex@prism.com"
                required
                className="w-full bg-black/60 border border-white/15 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-white/40 transition-colors"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-slate-300">
                  Password
                </label>
                <a
                  href="#forgot"
                  onClick={(e) => {
                    e.preventDefault();
                    alert('Please contact your administrator to reset your password.');
                  }}
                  className="text-xs text-slate-400 hover:text-white transition-colors"
                >
                  Forgot?
                </a>
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                required
                className="w-full bg-black/60 border border-white/15 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-white/40 transition-colors"
              />
            </div>

            <div className="flex items-center justify-between pt-1">
              <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="rounded bg-black border-white/20 text-white focus:ring-0 w-3.5 h-3.5 cursor-pointer"
                />
                <span>Remember me</span>
              </label>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-white hover:bg-slate-200 text-black font-semibold text-xs tracking-wide transition-colors mt-2 cursor-pointer disabled:opacity-50"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>

      {/* Footer */}
      <div className="max-w-md mx-auto w-full text-center text-xs text-slate-600 pb-4">
        © 2026 PRISM Technologies Inc. All rights reserved.
      </div>
    </div>
  );
}
