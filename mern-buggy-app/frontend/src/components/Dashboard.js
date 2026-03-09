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
          <button onClick={logout}>Logout</button>
        </div>
      </header>
      <main>
        <ProductList />
      </main>
    </div>
  );
};

export default Dashboard;
