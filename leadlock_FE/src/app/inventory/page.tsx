'use client';

import { useState, useEffect } from 'react';
import { api, DEMO_TENANT_ID, type InventoryItem } from '@/lib/api';

export default function InventoryPage() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [isAdding, setIsAdding] = useState(false);
  const [newItem, setNewItem] = useState({ name: '', price: '', mileage: '', location: '' });

  const loadItems = () => {
    api.getInventory(DEMO_TENANT_ID).then(setItems).catch(console.error);
  };

  useEffect(() => {
    loadItems();
  }, []);

  const handleAdd = async () => {
    if (!newItem.name) return;
    try {
      await api.createInventory(DEMO_TENANT_ID, {
        name: newItem.name,
        status: 'AVAILABLE',
        vertical_data: {
          price: newItem.price,
          mileage: newItem.mileage,
          location: newItem.location,
        }
      });
      setIsAdding(false);
      setNewItem({ name: '', price: '', mileage: '', location: '' });
      loadItems();
    } catch (err) {
      console.error(err);
      alert('Failed to add item');
    }
  };

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '0.5rem' }}>Inventory Sync</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            Manage the data the AI Agent uses to recommend products and services.
          </p>
        </div>
        <button className="btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }} onClick={() => setIsAdding(true)}>
          <span>+ Add Item</span>
        </button>
      </div>

      {isAdding && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div className="glass-card" style={{ padding: '2rem', width: '400px', background: 'var(--bg-card)' }}>
            <h2 style={{ marginBottom: '1rem', fontWeight: 600 }}>Add New Item</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <input placeholder="Vehicle Name" className="input-field" value={newItem.name} onChange={(e) => setNewItem({...newItem, name: e.target.value})} />
              <input placeholder="Price (e.g. $25,000)" className="input-field" value={newItem.price} onChange={(e) => setNewItem({...newItem, price: e.target.value})} />
              <input placeholder="Mileage (e.g. 15,000 miles)" className="input-field" value={newItem.mileage} onChange={(e) => setNewItem({...newItem, mileage: e.target.value})} />
              <input placeholder="Location" className="input-field" value={newItem.location} onChange={(e) => setNewItem({...newItem, location: e.target.value})} />
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1rem' }}>
                <button className="btn-outline" onClick={() => setIsAdding(false)}>Cancel</button>
                <button className="btn-primary" onClick={handleAdd}>Save</button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="glass-card">
        <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <input
            type="text"
            placeholder="Search inventory..."
            className="input-field"
            style={{ maxWidth: '300px' }}
          />
          <select className="input-field" style={{ maxWidth: '200px' }}>
            <option value="ALL">All Statuses</option>
            <option value="AVAILABLE">Available</option>
            <option value="RESERVED">Reserved</option>
            <option value="SOLD">Sold</option>
          </select>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>Item Name</th>
              <th>Status</th>
              <th>Price / Details</th>
              <th>Location</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td style={{ fontWeight: 500 }}>{item.name}</td>
                <td>
                  <span
                    style={{
                      padding: '0.25rem 0.625rem',
                      borderRadius: '999px',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      background: item.status === 'AVAILABLE' ? 'rgba(16, 185, 129, 0.15)' : item.status === 'RESERVED' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(100, 116, 139, 0.15)',
                      color: item.status === 'AVAILABLE' ? '#10b981' : item.status === 'RESERVED' ? '#f59e0b' : '#94a3b8',
                      border: `1px solid ${item.status === 'AVAILABLE' ? 'rgba(16, 185, 129, 0.3)' : item.status === 'RESERVED' ? 'rgba(245, 158, 11, 0.3)' : 'rgba(100, 116, 139, 0.3)'}`
                    }}
                  >
                    {item.status}
                  </span>
                </td>
                <td>
                  <div style={{ fontWeight: 600 }}>{item.vertical_data?.price}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{item.vertical_data?.mileage}</div>
                </td>
                <td>
                  <div style={{ fontSize: '0.875rem' }}>{item.vertical_data?.location}</div>
                </td>
                <td style={{ textAlign: 'right' }}>
                  <button className="btn-outline" style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}>Edit</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
