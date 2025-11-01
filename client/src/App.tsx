import { Route, Switch } from 'wouter';
import { Layout } from './components/Layout';
import { ChatPage } from './pages/ChatPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { AgentsPage } from './pages/AgentsPage';
import { DataSourcesPage } from './pages/DataSourcesPage';
import { AnalyticsPage } from './pages/AnalyticsPage';

function App() {
  return (
    <Layout>
      <Switch>
        <Route path="/" component={ChatPage} />
        <Route path="/documents" component={DocumentsPage} />
        <Route path="/agents" component={AgentsPage} />
        <Route path="/data-sources" component={DataSourcesPage} />
        <Route path="/analytics" component={AnalyticsPage} />
        <Route>404 - Page not found</Route>
      </Switch>
    </Layout>
  );
}

export default App;
