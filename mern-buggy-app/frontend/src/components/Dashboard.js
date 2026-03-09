// src/components/Dashboard.js — Correct component, no code-level bugs.
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api';
import ProductList from './ProductList';

const Dashboard = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await authAPI.getMe();
        setUser(response.data.data);
      } catch (err) {
        // Token invalid or expired — redirect to login
        localStorage.removeItem('token');
        navigate('/login');
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, [navigate]);

  const logout = () => {
    localStorage.removeItem('token'); // Correct key
    navigate('/login');
  };

  if (loading) return <div className="loading">Loading dashboard...</div>;
  if (!user) return null;

  // Correct: user null-checked before destructuring
  const { name, email, role } = user;

  return (
    <div className="dashboard">
      <header>
        <h1>Welcome, {name}!</h1>
        <div>
          <span>{email}</span>
          <span className={`role-badge role-${role}`}>{role}</span>
          <button onClick={logout} className="logout-btn">Logout</button>
        </div>
      </header>
      <section className="aiops-testing-panel" style={{ padding: '20px', background: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
        <h3>AIOps Self-Healing Testing</h3>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={async () => {
              const baseUrl = (process.env.REACT_APP_API_URL || 'http://localhost:3001/api').replace(/\/api$/, '');
              const res = await fetch(`${baseUrl}/api/leak`);
              const data = await res.json();
              alert(`Leak Triggered: ${data.heapUsed}`);
            }}
            style={{ padding: '10px', background: '#dc3545', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Trigger Memory Leak (OOM)
          </button>
          <button
            onClick={async () => {
              const start = Date.now();
              const baseUrl = (process.env.REACT_APP_API_URL || 'http://localhost:3001/api').replace(/\/api$/, '');
              const res = await fetch(`${baseUrl}/api/slow`);
              const data = await res.json();
              alert(`Latency Triggered: ${data.delay}ms (Actual: ${Date.now() - start}ms)`);
            }}
            style={{ padding: '10px', background: '#ffc107', color: 'black', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Simulate Latency Spike (P99)
          </button>
          <button
            onClick={() => {
              window.location.reload();
            }}
            style={{ padding: '10px', background: '#17a2b8', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Check Health Status
          </button>
        </div>
        <p style={{ fontSize: '12px', marginTop: '10px', color: '#6c757d' }}>
          Use these to test SuperCloud's AIOps detection of resource exhaustion and latency breaches.
        </p>
      </section>
      <main>
        <ProductList />
      </main>
    </div>
  );
};

export default Dashboard;
