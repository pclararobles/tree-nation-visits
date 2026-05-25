const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export type HourlyVisitCount = {
  hour: string;
  visit_count: number;
};

export type CustomerState = {
  customer_id: string;
  visit_count: number;
  trees_planted: number;
  last_connection_at: string;
};

export type CustomerSummary = {
  total_visits: number;
  total_trees_planted: number;
  items: CustomerState[];
};

export type VisitEventInput = {
  customer_id: string;
  occurred_at?: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function getHourlyVisits(): Promise<{ items: HourlyVisitCount[] }> {
  return request<{ items: HourlyVisitCount[] }>('/api/visits/hourly');
}

export function getCustomerSummary(): Promise<CustomerSummary> {
  return request<CustomerSummary>('/api/customers');
}

export function recordVisit(input: VisitEventInput): Promise<CustomerState> {
  return request<CustomerState>('/api/visits', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function getCustomer(customerId: string): Promise<CustomerState> {
  return request<CustomerState>(`/api/customers/${encodeURIComponent(customerId)}`);
}
