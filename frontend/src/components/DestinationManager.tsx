import { useEffect, useState } from 'react';
type Destination = { id: string; name: string; hec_url: string; hec_index: string; validation_status: string };
export function DestinationManager() {
  const [items, setItems] = useState<Destination[]>([]);
  const [message, setMessage] = useState('');
  useEffect(() => {fetch('/api/destinations/').then(r => {if (!r.ok) throw new Error('Destination load failed'); return r.json();}).then(setItems).catch(e => setMessage(String(e)));}, []);
  return <section className="panel" style={{padding: 24}}><h2>Destination Manager</h2><p>Profiles persist without secrets. Supply HEC credentials through server environment references or the destination API. TLS verification defaults to enabled.</p>{items.map(d => <article key={d.id}><h3>{d.name}</h3><p>{d.hec_url} — {d.hec_index} — {d.validation_status}</p><button onClick={async () => {try {const r = await fetch(`/api/destinations/${d.id}/test`, {method: 'POST'}); const data = await r.json(); setMessage(data.message || JSON.stringify(data));} catch(e) {setMessage(String(e));}}}>Test {d.name}</button></article>)}<p role="status">{message}</p></section>;
}
