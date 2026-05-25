import { FormEvent, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Activity, CalendarClock, RefreshCw, Send, Sprout, Trees } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { CustomerState, HourlyVisitCount, getCustomer, getHourlyVisits, recordVisit } from './api';

type ChartPoint = {
  hour: string;
  label: string;
  visits: number;
};

function formatHour(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function toChartPoint(item: HourlyVisitCount): ChartPoint {
  return {
    hour: item.hour,
    label: formatHour(item.hour),
    visits: item.visit_count,
  };
}

function toApiTimestamp(value: string) {
  return value ? new Date(value).toISOString() : undefined;
}

function useElementSize<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useLayoutEffect(() => {
    const node = ref.current;
    if (!node) {
      return undefined;
    }

    const updateSize = () => {
      const rect = node.getBoundingClientRect();
      setSize({
        width: Math.max(0, Math.floor(rect.width)),
        height: Math.max(0, Math.floor(rect.height)),
      });
    };

    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(node);

    return () => observer.disconnect();
  }, []);

  return [ref, size] as const;
}

export function App() {
  const [hourlyVisits, setHourlyVisits] = useState<HourlyVisitCount[]>([]);
  const [customerId, setCustomerId] = useState('customer-123');
  const [occurredAt, setOccurredAt] = useState('');
  const [customer, setCustomer] = useState<CustomerState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [chartRef, chartSize] = useElementSize<HTMLDivElement>();

  const chartData = useMemo(() => hourlyVisits.map(toChartPoint), [hourlyVisits]);
  const totalVisits = useMemo(
    () => hourlyVisits.reduce((total, item) => total + item.visit_count, 0),
    [hourlyVisits],
  );
  const peakHour = useMemo(
    () => hourlyVisits.reduce<HourlyVisitCount | null>((peak, item) => {
      if (!peak || item.visit_count > peak.visit_count) {
        return item;
      }
      return peak;
    }, null),
    [hourlyVisits],
  );

  async function refreshDashboard(nextCustomerId = customerId) {
    setIsLoading(true);
    setError(null);

    try {
      const [hourlyResponse, customerResponse] = await Promise.all([
        getHourlyVisits(),
        nextCustomerId.trim()
          ? getCustomer(nextCustomerId.trim()).catch(() => null)
          : Promise.resolve(null),
      ]);
      setHourlyVisits(hourlyResponse.items);
      setCustomer(customerResponse);
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
      setCustomer(updatedCustomer);
      setNotice(`Recorded visit ${updatedCustomer.visit_count} for ${updatedCustomer.customer_id}`);
      await refreshDashboard(trimmedCustomerId);
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
          <h1>Visit Tracker</h1>
        </div>
        <button className="icon-button" type="button" onClick={() => void refreshDashboard()} disabled={isLoading}>
          <RefreshCw size={18} aria-hidden="true" />
          <span>Refresh</span>
        </button>
      </header>

      <section className="summary-band" aria-label="Visit summary">
        <article className="metric-panel">
          <Activity size={20} aria-hidden="true" />
          <span>Total visits</span>
          <strong>{totalVisits}</strong>
        </article>
        <article className="metric-panel">
          <CalendarClock size={20} aria-hidden="true" />
          <span>Peak hour</span>
          <strong>{peakHour ? peakHour.visit_count : 0}</strong>
          <small>{peakHour ? formatHour(peakHour.hour) : 'No data'}</small>
        </article>
        <article className="metric-panel image-panel">
          <img
            src="https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=900&q=80"
            alt="Forest canopy"
          />
        </article>
      </section>

      <section className="workspace-grid">
        <div className="chart-surface">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Aggregated per hour</p>
              <h2>Shop visits</h2>
            </div>
            <span className="status-pill">{isLoading ? 'Loading' : `${chartData.length} hours`}</span>
          </div>

          <div className="chart-frame" ref={chartRef}>
            {chartData.length > 0 && chartSize.width > 0 && chartSize.height > 0 ? (
              <BarChart
                data={chartData}
                width={chartSize.width}
                height={chartSize.height}
                margin={{ top: 16, right: 20, bottom: 8, left: 0 }}
              >
                <CartesianGrid stroke="#d8e0d6" strokeDasharray="4 4" vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} minTickGap={24} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={36} />
                <Tooltip
                  cursor={{ fill: 'rgba(47, 122, 82, 0.08)' }}
                  contentStyle={{ borderRadius: 8, borderColor: '#cad5ca' }}
                />
                <Bar dataKey="visits" fill="#2f7a52" radius={[6, 6, 0, 0]} />
              </BarChart>
            ) : (
              <div className="empty-state">{chartData.length > 0 ? 'Loading chart...' : 'No visit events received yet.'}</div>
            )}
          </div>
        </div>

        <aside className="side-panel">
          <form onSubmit={handleSubmit}>
            <div className="section-heading compact">
              <div>
                <p className="eyebrow">Device event</p>
                <h2>Record visit</h2>
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
              <span>{isSubmitting ? 'Recording' : 'Record visit'}</span>
            </button>
          </form>

          <div className="customer-readout">
            <div className="section-heading compact">
              <div>
                <p className="eyebrow">Customer</p>
                <h2>Current state</h2>
              </div>
              <Trees size={20} aria-hidden="true" />
            </div>

            {customer ? (
              <dl>
                <div>
                  <dt>Visits</dt>
                  <dd>{customer.visit_count}</dd>
                </div>
                <div>
                  <dt>Trees</dt>
                  <dd>{customer.trees_planted}</dd>
                </div>
                <div>
                  <dt>Last connection</dt>
                  <dd>{formatHour(customer.last_connection_at)}</dd>
                </div>
              </dl>
            ) : (
              <p className="muted">No customer selected.</p>
            )}
          </div>

          {(error || notice) && <p className={error ? 'message error' : 'message'}>{error ?? notice}</p>}
        </aside>
      </section>
    </main>
  );
}
