import React, { useState, useEffect } from 'react';
import api from '../api';
function BrandSetup({ onBrandSelected }) {
  const [clients, setClients]       = useState([]);
  const [brands, setBrands]         = useState([]);
  const [newClient, setNewClient]   = useState('');
  const [newBrand, setNewBrand]     = useState({ name: '', domain: '', client_id: '' });
  const [loading, setLoading]       = useState(false);
  const [message, setMessage]       = useState('');

  // Load existing clients and brands on mount
  useEffect(() => {
    fetchClients();
    fetchBrands();
  }, []);

  const fetchClients = async () => {
    try {
      const res = await api.get(`/clients`);
      setClients(res.data);
    } catch (e) {
      console.error('Error fetching clients:', e);
    }
  };

  const fetchBrands = async () => {
    try {
      const res = await api.get(`/brands`);
      setBrands(res.data);
    } catch (e) {
      console.error('Error fetching brands:', e);
    }
  };

  const createClient = async () => {
    if (!newClient.trim()) return;
    try {
      await api.post(`/clients`, { name: newClient });
      setNewClient('');
      setMessage('✅ Client created!');
      fetchClients();
    } catch (e) {
      setMessage('❌ Error creating client');
    }
  };

  const createBrand = async () => {
    if (!newBrand.name || !newBrand.domain || !newBrand.client_id) {
      setMessage('❌ Please fill all fields');
      return;
    }
    setLoading(true);
    try {
      await api.post(`/brands`, {
        name:      newBrand.name,
        domain:    newBrand.domain,
        client_id: newBrand.client_id,
        geos:      ['IN', 'AE', 'GB'],
      });
      setMessage('✅ Brand created!');
      setNewBrand({ name: '', domain: '', client_id: '' });
      fetchBrands();
    } catch (e) {
      setMessage('❌ Error creating brand');
    }
    setLoading(false);
  };

  return (
    <div>
      <h2 style={{ marginBottom: 24, fontSize: 22 }}>
        Brand Setup
      </h2>

      {message && (
        <div style={{
          padding: '10px 16px',
          background: '#f0f7ff',
          borderRadius: 8,
          marginBottom: 16,
          fontSize: 14,
        }}>
          {message}
        </div>
      )}

      {/* Create Client */}
      <div className="card">
        <h2>Create a Client</h2>
        <label>Company Name</label>
        <input
          value={newClient}
          onChange={e => setNewClient(e.target.value)}
          placeholder="e.g. Landmark Group"
        />
        <button className="btn btn-secondary" onClick={createClient}>
          Create Client
        </button>
      </div>

      {/* Create Brand */}
      <div className="card">
        <h2>Add a Brand to Track</h2>

        <label>Select Client</label>
        <select
          value={newBrand.client_id}
          onChange={e => setNewBrand({ ...newBrand, client_id: e.target.value })}
        >
          <option value="">-- Select a client --</option>
          {clients.map(c => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>

        <label>Brand Name</label>
        <input
          value={newBrand.name}
          onChange={e => setNewBrand({ ...newBrand, name: e.target.value })}
          placeholder="e.g. Mochi Shoes"
        />

        <label>Domain</label>
        <input
          value={newBrand.domain}
          onChange={e => setNewBrand({ ...newBrand, domain: e.target.value })}
          placeholder="e.g. mochi.in"
        />

        <button
          className="btn btn-primary"
          onClick={createBrand}
          disabled={loading}
          style={{ marginTop: 8 }}
        >
          {loading ? 'Creating...' : 'Add Brand'}
        </button>
      </div>

      {/* Existing Brands */}
      {brands.length > 0 && (
        <div className="card">
          <h2>Select a Brand to View Dashboard</h2>
          <table>
            <thead>
              <tr>
                <th>Brand</th>
                <th>Domain</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {brands.map(b => (
                <tr key={b.id}>
                  <td>{b.name}</td>
                  <td>{b.domain}</td>
                  <td>
                    <button
                      className="btn btn-primary"
                      onClick={() => onBrandSelected(b)}
                    >
                      View Dashboard →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default BrandSetup;