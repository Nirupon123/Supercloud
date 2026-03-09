// ============================================================
// controllers/productController.js
//
// CLOUD/AIOPS ERROR IN THIS FILE:
//
// [ERROR-12] CPU SPIKE / EVENT LOOP BLOCKING:
//   getProductById performs a heavy synchronous computation in the hot path.
//   Node.js is single-threaded — blocking the event loop for >100ms stalls
//   ALL concurrent requests on this pod. Under load this manifests as:
//   - CPU utilization spikes to 100%
//   - All request latencies spike simultaneously (not just this endpoint)
//   - AIOps detects CPU p99 breach + correlated latency spike
//   - Triggers: horizontal scale-out, CPU throttle alert
// ============================================================

const Product = require('../models/Product');
const logger = require('../config/logger');

// @desc   Get all products
// @route  GET /api/products
// @access Public
const getAllProducts = async (req, res, next) => {
  try {
    const products = await Product.find().limit(50);
    logger.info(`Fetched ${products.length} products`);
    res.json({ success: true, count: products.length, data: products });
  } catch (error) {
    next(error);
  }
};

// @desc   Get single product
// @route  GET /api/products/:id
// @access Public
const getProductById = async (req, res, next) => {
  try {
    const product = await Product.findById(req.params.id).populate('createdBy', 'name email');

    if (!product) {
      return res.status(404).json({ message: 'Product not found' });
    }

    // [ERROR-12] CPU-BLOCKING SYNCHRONOUS OPERATION in the hot request path.
    // Simulates a serialization transform that runs synchronously.
    // On a small dataset this is fast. At scale (large product objects,
    // frequent requests), this blocks the event loop, spiking CPU to 100%
    // and stalling all other concurrent requests on this Node.js process.
    let serialized = product.toObject();
    for (let i = 0; i < 5000; i++) {
      // Repeated synchronous deep clone — blocks event loop
      serialized = JSON.parse(JSON.stringify(serialized));
    }
    // This simulates what happens when a poorly-optimised transformation
    // (e.g., template rendering, schema validation) runs eagerly in-process.

    logger.info(`Returning product: ${product._id}`);
    res.json({ success: true, data: serialized });
  } catch (error) {
    next(error);
  }
};

// @desc   Create product
// @route  POST /api/products
// @access Private
const createProduct = async (req, res, next) => {
  try {
    const product = await Product.create({
      ...req.body,
      createdBy: req.user._id,
    });
    logger.info(`Product created: ${product._id}`);
    res.status(201).json({ success: true, data: product });
  } catch (error) {
    next(error);
  }
};

// @desc   Update product
// @route  PUT /api/products/:id
// @access Private
const updateProduct = async (req, res, next) => {
  try {
    const product = await Product.findByIdAndUpdate(
      req.params.id,
      req.body,
      { new: true, runValidators: true }
    );
    if (!product) {
      return res.status(404).json({ message: 'Product not found' });
    }
    logger.info(`Product updated: ${product._id}`);
    res.json({ success: true, data: product });
  } catch (error) {
    next(error);
  }
};

// @desc   Delete product
// @route  DELETE /api/products/:id
// @access Private
const deleteProduct = async (req, res, next) => {
  try {
    const product = await Product.findByIdAndDelete(req.params.id);
    if (!product) {
      return res.status(404).json({ message: 'Product not found' });
    }
    logger.info(`Product deleted: ${req.params.id}`);
    res.json({ success: true, message: 'Product deleted' });
  } catch (error) {
    next(error);
  }
};

module.exports = { getAllProducts, getProductById, createProduct, updateProduct, deleteProduct };
