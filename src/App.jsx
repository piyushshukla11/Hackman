import React, { useState } from 'react';
import LandingPage from '../landing/LandingPage';
import AuthPage, { USER_ROLES } from './pages/AuthPage';
import Navbar from './components/layout/Navbar';
import Sidebar from './components/layout/Sidebar';

import OnboardingModal from './components/OnboardingModal';

// Pages
import OverviewPage from './pages/OverviewPage';
import StreamPage from './pages/StreamPage';
import IssuesPage from './pages/IssuesPage';
import ReviewXRayPage from './pages/ReviewXRayPage';
import TimelinePage from './pages/TimelinePage';
import ComparePage from './pages/ComparePage';
import ProductsPage from './pages/ProductsPage';
import SeriousPage from './pages/SeriousPage';
import InvestigationsPage from './pages/InvestigationsPage';
import SourcesPage from './pages/SourcesPage';
import ReportsPage from './pages/ReportsPage';
import SettingsPage from './pages/SettingsPage';
import JudgePage from './pages/JudgePage';

export default function App() {
  const [currentView, setCurrentView] = useState('landing'); // 'landing' | 'auth' | 'app'
  const [currentUser, setCurrentUser] = useState({
    name: 'Alex Rivera',
    email: 'alex.design@paralink.tech',
    empId: 'EMP-4921',
    jobTitle: 'Staff Product Designer',
    role: 'designer',
    roleData: USER_ROLES[0],
  });

  const [activeTab, setActiveTab] = useState('overview');
  const [selectedProduct, setSelectedProduct] = useState('prod_001');
  const [includeQuarantined, setIncludeQuarantined] = useState(false);
  const [inspectedIssueId, setInspectedIssueId] = useState('ISS-0716');
  const [inspectedReviewId, setInspectedReviewId] = useState('REV-98214');
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);

  // Handle saving workspace personalization preferences (F27)
  const handleSavePreferences = ({ roleTitle, allowedTabs }) => {
    setCurrentUser((prev) => ({
      ...prev,
      jobTitle: roleTitle,
      roleData: {
        ...prev.roleData,
        title: roleTitle,
        allowedTabs,
      },
    }));
    if (!allowedTabs.includes(activeTab)) {
      setActiveTab(allowedTabs[0] || 'overview');
    }
  };

  // Handle successful authentication: role is locked to the authenticated user's ID
  const handleAuthenticated = (userData) => {
    setCurrentUser(userData);
    setActiveTab(userData.roleData.defaultTab || 'overview');
    setCurrentView('app');
  };

  // Navigation handlers
  const handleNavigateIssue = (issueId) => {
    setInspectedIssueId(issueId);
    setActiveTab('issues');
  };

  const handleNavigateXRay = (reviewId) => {
    setInspectedReviewId(reviewId);
    setActiveTab('xray');
  };

  // Render Landing View
  if (currentView === 'landing') {
    return <LandingPage onEnter={() => setCurrentView('auth')} />;
  }

  // Render Role-Tailored Authentication Page
  if (currentView === 'auth') {
    return (
      <AuthPage
        onAuthenticated={handleAuthenticated}
        onBackToLanding={() => setCurrentView('landing')}
      />
    );
  }

  // Render Main Application Shell
  const allowedTabs = currentUser?.roleData?.allowedTabs || [];

  return (
    <div className="min-h-screen bg-[#121316] text-slate-100 flex flex-col font-sans select-none antialiased">
      {/* Top Navigation */}
      <Navbar
        selectedProduct={selectedProduct}
        onSelectProduct={setSelectedProduct}
        currentUser={currentUser}
        onSwitchUser={() => setCurrentView('auth')}
        onOpenOnboarding={() => setIsOnboardingOpen(true)}
        includeQuarantined={includeQuarantined}
        onToggleQuarantined={() => setIncludeQuarantined(!includeQuarantined)}
        onNavigateLanding={() => setCurrentView('landing')}
      />

      {/* Main Body: Filtered Sidebar + Viewport */}
      <div className="flex-1 flex overflow-hidden bg-[#121316]">
        {/* Left Filtered Sidebar (shows ONLY relevant views) */}
        <Sidebar
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          allowedTabs={allowedTabs}
        />

        {/* Viewport Content */}
        <main className="flex-1 overflow-y-auto p-8 bg-[#121316] text-slate-100">
          <div className="max-w-7xl mx-auto">
            {activeTab === 'overview' && (
              <OverviewPage
                selectedProduct={selectedProduct}
                onNavigateIssue={handleNavigateIssue}
                roleLens={currentUser.role}
              />
            )}
            {activeTab === 'stream' && <StreamPage />}
            {activeTab === 'issues' && (
              <IssuesPage
                selectedProduct={selectedProduct}
                initialIssueId={inspectedIssueId}
                onNavigateXRay={handleNavigateXRay}
              />
            )}
            {activeTab === 'xray' && (
              <ReviewXRayPage
                selectedProduct={selectedProduct}
                reviewId={inspectedReviewId}
              />
            )}
            {activeTab === 'timeline' && <TimelinePage selectedProduct={selectedProduct} />}
            {activeTab === 'compare' && <ComparePage selectedProduct={selectedProduct} />}
            {activeTab === 'products' && <ProductsPage selectedProduct={selectedProduct} onSelectProduct={setSelectedProduct} />}
            {activeTab === 'serious' && <SeriousPage selectedProduct={selectedProduct} />}
            {activeTab === 'investigations' && <InvestigationsPage selectedProduct={selectedProduct} />}
            {activeTab === 'sources' && <SourcesPage />}
            {activeTab === 'reports' && <ReportsPage selectedProduct={selectedProduct} />}
            {activeTab === 'settings' && <SettingsPage />}
            {activeTab === 'judge' && (
              <JudgePage
                onNavigateTab={setActiveTab}
                onNavigateIssue={handleNavigateIssue}
                onNavigateXRay={handleNavigateXRay}
              />
            )}
          </div>
        </main>
      </div>

      {/* F27 Workspace Personalization & Onboarding Modal */}
      <OnboardingModal
        isOpen={isOnboardingOpen}
        onClose={() => setIsOnboardingOpen(false)}
        currentUser={currentUser}
        onSavePreferences={handleSavePreferences}
      />
    </div>
  );
}
