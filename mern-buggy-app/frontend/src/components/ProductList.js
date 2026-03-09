// src/components/ProductList.js — Correct component, no code-level bugs.
import React, { useState, useEffect, useCallback } from 'react';
import { productAPI } from '../services/api';

const ProductList = () => {
  const [products, setProducts] = useState([]); // Correct: initialized as array
  const [allProducts, setAllProducts] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchProducts = useCallback(async () => {
    try {
      setLoading(true);
      const response = await productAPI.getAll();
      setProducts(response.data.data);
      setAllProducts(response.data.data); // Keep original for search reset
    } catch (err) {
      setError('Failed to load products. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProducts();
    return () => {}; // Cleanup
  }, [fetchProducts]);

  const handleSearch = (e) => {
    const term = e.target.value;
    setSearchTerm(term);
    // Non-destructive filter — always filters from allProducts
    const filtered = allProducts.filter((p) =>
      p.name.toLowerCase().includes(term.toLowerCase())
    );
    setProducts(filtered);
  };

  const handleDelete = async (id) => {
    try {
      await productAPI.delete(id);
      // Correct: update local state after delete
      setProducts((prev) => prev.filter((p) => p._id !== id));
      setAllProducts((prev) => prev.filter((p) => p._id !== id));
    } catch (err) {
      setError('Failed to delete product.');
    }
  };

  if (loading) return <div className="loading">Loading products...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="product-list">
      <h2>Products ({products.length})</h2>
      <input
        type="text"
        placeholder="Search products..."
        value={searchTerm}
        onChange={handleSearch}
      />
      {products.length === 0 ? (
        <p className="empty">No products found.</p>
      ) : (
        <div className="products-grid">
          {products.map((product) => ( // Correct: products is always an array
            <div className="product-card" key={product._id}> {/* Correct: key prop present */}
              <h3>{product.name}</h3>
              <p>Price: ${product.price.toFixed(2)}</p> {/* Correct: price is Number */}
              <p>Category: {product.category}</p>
              <p>Stock: {product.stock}</p>
              <button onClick={() => handleDelete(product._id)}>Delete</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProductList;
