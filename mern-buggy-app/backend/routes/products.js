// ============================================================
// routes/products.js
//
// CLOUD/AIOPS ERROR IN THIS FILE:
// [ERROR-10 continued] cacheMiddleware applied to GET /api/products.
//   Feeds the unbounded in-memory cache in middleware/cache.js.
//   Each unique query string variation grows the heap permanently.
// ============================================================
const express = require('express');
const router = express.Router();
const { protect, authorize } = require('../middleware/auth');
const { cacheMiddleware } = require('../middleware/cache');
const {
  getAllProducts,
  getProductById,
  createProduct,
  updateProduct,
  deleteProduct,
} = require('../controllers/productController');

// [ERROR-10] cacheMiddleware populates the leaking in-memory cache
router.get('/', cacheMiddleware(60), getAllProducts);

// [ERROR-12] getProductById contains the CPU-blocking sync loop
router.get('/:id', getProductById);

router.post('/', protect, createProduct);
router.put('/:id', protect, authorize('admin'), updateProduct);
router.delete('/:id', protect, authorize('admin'), deleteProduct);

module.exports = router;
