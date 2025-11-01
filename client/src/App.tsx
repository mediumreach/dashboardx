import { Route, Switch, Redirect } from 'wouter';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Layout } from './components/Layout';
import { AuthPage } from './pages/AuthPage';
import { ChatPage } from './pages/ChatPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { AgentsPage } from './pages/AgentsPage';
import { DataSourcesPage } from './pages/DataSourcesPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { UsersPage } from './pages/UsersPage';

function ProtectedRoute({ component: Component }: { component: React.ComponentType }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-slate-50 to-cyan-50">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-cyan-200 border-t-cyan-600 rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Redirect to="/auth" />;
  }

  return <Component />;
}

function AppContent() {
  const { user } = useAuth();

  if (!user) {
    return (
      <Switch>
        <Route path="/auth" component={AuthPage} />
        <Route path="/:rest*">
          <Redirect to="/auth" />
        </Route>
      </Switch>
    );
  }

  return (
    <Layout>
      <Switch>
        <Route path="/" component={() => <ProtectedRoute component={ChatPage} />} />
        <Route path="/documents" component={() => <ProtectedRoute component={DocumentsPage} />} />
        <Route path="/agents" component={() => <ProtectedRoute component={AgentsPage} />} />
        <Route path="/data-sources" component={() => <ProtectedRoute component={DataSourcesPage} />} />
        <Route path="/analytics" component={() => <ProtectedRoute component={AnalyticsPage} />} />
        <Route path="/users" component={() => <ProtectedRoute component={UsersPage} />} />
        <Route path="/auth">
          <Redirect to="/" />
        </Route>
        <Route>404 - Page not found</Route>
      </Switch>
    </Layout>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
