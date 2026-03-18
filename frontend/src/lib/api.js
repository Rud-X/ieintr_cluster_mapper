const BASE = '/api';

async function req(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const fetchData = () => req('/data');

export const updateCompany = (id, body) =>
  req(`/companies/${id}`, { method: 'PUT', body: JSON.stringify(body) });

export const createFlow = (body) =>
  req('/flows', { method: 'POST', body: JSON.stringify(body) });

export const updateFlow = (id, body) =>
  req(`/flows/${id}`, { method: 'PUT', body: JSON.stringify(body) });

export const deleteFlow = (id) =>
  req(`/flows/${id}`, { method: 'DELETE' });
