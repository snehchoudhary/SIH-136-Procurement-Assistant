import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { LoadingSpinner } from './components/ui/LoadingSpinner';

const LandingPage = React.lazy(() => import('./pages/LandingPage'));
const WorkspaceDashboard = React.lazy(() => import('./pages/WorkspaceDashboard'));
const DesignShowcasePage = React.lazy(() => import('./pages/DesignShowcasePage'));
const AuditPage = React.lazy(() => import('./pages/AuditPage'));
const ChallengeBuilderPage = React.lazy(() => import('./pages/ChallengeBuilderPage'));
const DiscoveryPage = React.lazy(() => import('./pages/DiscoveryPage'));
const EligibilityHelpPage = React.lazy(() => import('./pages/EligibilityHelpPage'));
const EvaluatorWorkspacePage = React.lazy(() => import('./pages/EvaluatorWorkspacePage'));
const CommitteeWorkspacePage = React.lazy(() => import('./pages/CommitteeWorkspacePage'));
const AgreementWorkspacePage = React.lazy(() => import('./pages/AgreementWorkspacePage'));
const ValidatorWorkspacePage = React.lazy(() => import('./pages/ValidatorWorkspacePage'));
const FinanceDashboardPage = React.lazy(() => import('./pages/FinanceDashboardPage'));
const TransferAssessmentPage = React.lazy(() => import('./pages/TransferAssessmentPage'));
const PassportPage = React.lazy(() => import('./pages/PassportPage'));
const PublicVerifyPage = React.lazy(() => import('./pages/PublicVerifyPage'));
const NotFoundPage = React.lazy(() => import('./pages/NotFoundPage'));

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className='h-screen w-screen flex items-center justify-center bg-bg'><LoadingSpinner size='lg' /></div>}>
        <Routes>
          <Route path='/' element={<LandingPage />} />
          <Route path='/verify/:id' element={<PublicVerifyPage />} />
          <Route path='*' element={<NotFoundPage />} />
          <Route element={<AppShell />}>
            <Route path='/workspace' element={<WorkspaceDashboard />} />
            <Route path='/components' element={<DesignShowcasePage />} />
            <Route path='/audit' element={<AuditPage />} />
            <Route path='/challenges/new' element={<ChallengeBuilderPage />} />
            <Route path='/discover' element={<DiscoveryPage />} />
            <Route path='/eligibility' element={<EligibilityHelpPage />} />
            <Route path='/evaluations' element={<EvaluatorWorkspacePage />} />
            <Route path='/committee' element={<CommitteeWorkspacePage />} />
            <Route path='/agreements' element={<AgreementWorkspacePage />} />
            <Route path='/evidence' element={<ValidatorWorkspacePage />} />
            <Route path='/finance' element={<FinanceDashboardPage />} />
            <Route path='/scale' element={<TransferAssessmentPage />} />
            <Route path='/passport/:id' element={<PassportPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
