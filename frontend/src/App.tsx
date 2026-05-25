import { FormEvent, useEffect, useState } from 'react';
import { Activity, Leaf, RefreshCw, Send, Sprout, Trees, Users } from 'lucide-react';
import { CustomerSummary, getCustomerSummary, recordVisit } from './api';

function formatHour(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function toApiTimestamp(value: string) {
  return value ? new Date(value).toISOString() : undefined;
}

function getCurrentView() {
  return window.location.pathname === '/admin' ? 'admin' : 'public';
}

export function App() {
  const [currentView, setCurrentView] = useState(getCurrentView);

  useEffect(() => {
    const handleNavigation = () => setCurrentView(getCurrentView());

    window.addEventListener('popstate', handleNavigation);
    return () => window.removeEventListener('popstate', handleNavigation);
  }, []);

  function navigateTo(path: string) {
    window.history.pushState(null, '', path);
    setCurrentView(getCurrentView());
  }

  return currentView === 'admin' ? (
    <AdminDashboard onNavigate={navigateTo} />
  ) : (
    <PublicDashboard onNavigate={navigateTo} />
  );
}

type DashboardProps = {
  onNavigate: (path: string) => void;
};

function PublicDashboard({ onNavigate }: DashboardProps) {
  const [customerSummary, setCustomerSummary] = useState<CustomerSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const totalVisits = customerSummary?.total_visits ?? 0;
  const totalTreesPlanted = customerSummary?.total_trees_planted ?? 0;

  async function refreshSummary() {
    setIsLoading(true);
    setError(null);

    try {
      setCustomerSummary(await getCustomerSummary());
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : 'Unable to refresh impact summary');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void refreshSummary();
  }, []);

  return (
    <main className="app-shell public-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Tree Nation</p>
          <h1>Forest Impact</h1>
        </div>
        <nav className="top-actions" aria-label="Main navigation">
          <button className="icon-button" type="button" onClick={() => void refreshSummary()} disabled={isLoading}>
            <RefreshCw size={18} aria-hidden="true" />
            <span>Refresh</span>
          </button>
          <button className="icon-button" type="button" onClick={() => onNavigate('/admin')}>
            <Users size={18} aria-hidden="true" />
            <span>Admin</span>
          </button>
        </nav>
      </header>

      <section className="public-hero" aria-label="Tree planting impact">
        <img
          src="https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=1400&q=80"
          alt="Forest canopy"
        />
        <div className="hero-content">
          <p className="eyebrow">Live contribution</p>
          <strong>{totalTreesPlanted}</strong>
          <span>Trees planted from customer visits</span>
        </div>
      </section>

      <section className="summary-band" aria-label="Public impact summary">
        <article className="metric-panel">
          <Trees size={20} aria-hidden="true" />
          <span>Trees planted</span>
          <strong>{totalTreesPlanted}</strong>
          <small>Calculated from customer milestones</small>
        </article>
        <article className="metric-panel">
          <Activity size={20} aria-hidden="true" />
          <span>Total visits</span>
          <strong>{totalVisits}</strong>
          <small>Aggregated across all customers</small>
        </article>
        <article className="metric-panel">
          <Leaf size={20} aria-hidden="true" />
          <span>Public view</span>
          <strong>Live</strong>
          <small>Aggregate impact only</small>
        </article>
      </section>

      {error && <p className="message error">{error}</p>}
    </main>
  );
}

function AdminDashboard({ onNavigate }: DashboardProps) {
  const [customerSummary, setCustomerSummary] = useState<CustomerSummary | null>(null);
  const [customerId, setCustomerId] = useState('customer-123');
  const [occurredAt, setOccurredAt] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const customers = customerSummary?.items ?? [];
  const totalVisits = customerSummary?.total_visits ?? 0;
  const totalTreesPlanted = customerSummary?.total_trees_planted ?? 0;

  async function refreshDashboard() {
    setIsLoading(true);
    setError(null);

    try {
      setCustomerSummary(await getCustomerSummary());
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : 'Unable to refresh dashboard');
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedCustomerId = customerId.trim();

    if (!trimmedCustomerId) {
      setError('Customer id is required');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setNotice(null);

    try {
      const updatedCustomer = await recordVisit({
        customer_id: trimmedCustomerId,
        occurred_at: toApiTimestamp(occurredAt),
      });
      setNotice(`Recorded visit ${updatedCustomer.visit_count} for ${updatedCustomer.customer_id}`);
      await refreshDashboard();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : 'Unable to record visit');
    } finally {
      setIsSubmitting(false);
    }
  }

  useEffect(() => {
    void refreshDashboard();
  }, []);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Tree Nation</p>
          <h1>Admin Dashboard</h1>
        </div>
        <nav className="top-actions" aria-label="Main navigation">
          <button className="icon-button" type="button" onClick={() => onNavigate('/')}>
            <Leaf size={18} aria-hidden="true" />
            <span>Public</span>
          </button>
          <button className="icon-button" type="button" onClick={() => void refreshDashboard()} disabled={isLoading}>
            <RefreshCw size={18} aria-hidden="true" />
            <span>Refresh</span>
          </button>
        </nav>
      </header>

      <section className="summary-band" aria-label="Visit summary">
        <article className="metric-panel">
          <Activity size={20} aria-hidden="true" />
          <span>Total visits</span>
          <strong>{totalVisits}</strong>
        </article>
        <article className="metric-panel">
          <Trees size={20} aria-hidden="true" />
          <span>Trees planted</span>
          <strong>{totalTreesPlanted}</strong>
          <small>Calculated per customer</small>
        </article>
      </section>

      <section className="admin-sections">
        <div className="admin-lower-grid">
          <section className="side-panel admin-section" aria-label="Debug tools">
            <form onSubmit={handleSubmit}>
              <div className="section-heading compact">
                <div>
                  <p className="eyebrow">Debug tools</p>
                  <h2>Add customer visit</h2>
                </div>
                <Send size={20} aria-hidden="true" />
              </div>

              <label>
                <span>Customer id</span>
                <input value={customerId} onChange={(event) => setCustomerId(event.target.value)} />
              </label>

              <label>
                <span>Occurred at</span>
                <input
                  type="datetime-local"
                  value={occurredAt}
                  onChange={(event) => setOccurredAt(event.target.value)}
                />
              </label>

              <button className="primary-button" type="submit" disabled={isSubmitting}>
                <Sprout size={18} aria-hidden="true" />
                <span>{isSubmitting ? 'Adding' : 'Add visit'}</span>
              </button>
            </form>

            {(error || notice) && <p className={error ? 'message error' : 'message'}>{error ?? notice}</p>}
          </section>

          <section className="customer-readout admin-section" aria-label="Registered customers">
            <div className="section-heading compact">
              <div>
                <p className="eyebrow">Registered customers</p>
                <h2>Customer list</h2>
              </div>
              <Users size={20} aria-hidden="true" />
            </div>

            {customers.length > 0 ? (
              <table className="customer-table" aria-label="Customer visit totals">
                <thead>
                  <tr>
                    <th scope="col">Customer</th>
                    <th scope="col">Visits</th>
                    <th scope="col">Trees</th>
                    <th scope="col">Last visit</th>
                  </tr>
                </thead>
                <tbody>
                  {customers.map((customer) => (
                    <tr key={customer.customer_id}>
                      <td className="customer-id" title={customer.customer_id}>
                        {customer.customer_id}
                      </td>
                      <td>{customer.visit_count}</td>
                      <td>{customer.trees_planted}</td>
                      <td>{formatHour(customer.last_connection_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="muted">No customers recorded yet.</p>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}
