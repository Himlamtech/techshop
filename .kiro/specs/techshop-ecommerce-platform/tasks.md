# Implementation Plan: TechShop E-Commerce Platform

## Overview

This implementation plan breaks down the TechShop microservices e-commerce platform into incremental coding tasks organized by development phases. Each phase builds on the previous one, starting with infrastructure and foundational shared code, then layering services and features progressively. The stack uses Django REST Framework for 7 business services, FastAPI for the AI service, PostgreSQL + MySQL databases, Nginx gateway, and React/Vite frontend.

## Tasks

- [x] 1. Phase 0 — Repository Stabilization and Infrastructure
  - [x] 1.1 Create Docker Compose file with all services, databases, networks, and volumes
    - Define 8 application services, 2 MySQL containers (identity_db, payment_db), 6 PostgreSQL containers (catalog_db, cart_db, order_db, shipping_db, review_db, ai_db with pgvector)
    - Configure two Docker networks: `public` (gateway only) and `internal` (all services + databases)
    - Configure named volumes for all database containers
    - Add healthchecks for all database containers (interval 10s, timeout 5s, retries 10)
    - Only expose port 80 on the host via gateway
    - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6_

  - [x] 1.2 Create Nginx gateway configuration and Dockerfile
    - Configure routing for all service prefixes: /api/auth/, /api/catalog/, /api/cart/, /api/orders/, /api/payments/, /api/shipping/, /api/reviews/, /api/ai/
    - Route / to frontend:3000
    - Inject X-Request-ID header on all proxied requests
    - Propagate Authorization header to all backend services
    - Set client_max_body_size to 20m
    - Set proxy_read_timeout to 120s for AI endpoints
    - _Requirements: 20.4, 21.5, 21.6, 25.6_

  - [x] 1.3 Create Django service scaffold with shared core app
    - Create base Dockerfile for Django services (Python 3.11, gunicorn)
    - Create a template service structure: config/ (settings, urls, wsgi), apps/core/
    - Implement `apps/core/responses.py` — standard envelope wrapper (success/error format)
    - Implement `apps/core/exceptions.py` — custom exception classes mapped to error codes
    - Implement `apps/core/middleware.py` — request ID generation, structured JSON logging, JWT extraction
    - Implement `apps/core/pagination.py` — page-based pagination with standard meta format
    - Implement `apps/core/permissions.py` — base RBAC permission classes (IsAdmin, IsStaff, IsCustomer, IsOwner)
    - Implement `apps/core/http_client.py` — ServiceClient wrapper with timeout, header propagation, logging
    - _Requirements: 18.1, 18.2, 18.3, 18.5, 18.6, 18.7, 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7, 20.3, 20.4, 20.5_

  - [x] 1.4 Create .env.example files for all services
    - Include DATABASE_URL, SECRET_KEY, JWT_PUBLIC_KEY, service URLs, LOG_LEVEL
    - Create root .env.example with compose-level variables
    - Add .env to .gitignore
    - _Requirements: 25.1_

  - [x] 1.5 Create healthcheck endpoints for all Django services
    - Implement GET /healthz returning {"status": "ok"} with HTTP 200 when process is alive
    - Implement GET /readyz returning {"status": "ready"} with HTTP 200 when DB connection is healthy, or {"status": "not_ready", "checks": [...]} with HTTP 503 when dependencies are unreachable
    - Add Docker healthcheck configuration for each application service container (interval 10s, retries 5)
    - _Requirements: 20.1, 20.2, 21.7_

  - [x] 1.6 Create React/Vite frontend scaffold with API client
    - Initialize Vite + React + TypeScript project in frontend/
    - Create `src/lib/api-client.ts` with standard envelope handling, auth token injection, error parsing
    - Create `src/types/` with shared TypeScript interfaces for API responses
    - Create Dockerfile for frontend (node:20, npm build, serve)
    - _Requirements: 22.9_

- [x] 2. Checkpoint — Verify infrastructure boots
  - Run `docker compose up -d` and verify all containers reach healthy status
  - Verify gateway routes return 502 (services not yet implemented) or healthcheck 200
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Phase 1 — Catalog Service + Frontend Product Display
  - [x] 3.1 Implement Catalog Service models and migrations
    - Create Category model with UUID PK, name, slug, parent_id (self-referential FK), is_active, level (1-3 enforced)
    - Create Product model with UUID PK, sku (unique), name, slug, description, price (Decimal 0.01-999999999.99), stock (0-999999), brand, category FK, status (active/inactive), attributes (JSONField), rating_avg, rating_count, timestamps
    - Create ProductImage model with UUID PK, product FK, image_url, is_primary, sort_order; constraint: exactly one primary per product, max 20 images per product
    - Generate and apply migrations
    - _Requirements: 4.1, 4.5, 6.1_

  - [x] 3.2 Implement Catalog Service serializers and validation
    - Create CategorySerializer with nested children support
    - Create ProductSerializer with image nesting, field validation (price range, stock range, name length)
    - Create ProductImageSerializer
    - Create ProductImportSerializer for DummyJSON field mapping
    - Create filter/search query parameter serializers
    - _Requirements: 4.1, 4.2, 5.1, 5.2, 5.3, 5.4_

  - [x] 3.3 Implement Catalog Service views and URL routing
    - GET /api/v1/products — paginated list with filters (category, brand, price range, rating), sorting (price, rating, newest), keyword search
    - GET /api/v1/products/{id} — full product detail with images and attributes
    - POST /api/v1/products — admin create product
    - PATCH /api/v1/products/{id} — admin update product
    - DELETE /api/v1/products/{id} — admin soft-delete (set inactive)
    - POST /api/v1/products/validate-bulk — internal endpoint for cart/order validation
    - POST /api/v1/products/import — admin trigger DummyJSON import
    - GET /api/v1/categories — list all active categories with hierarchy
    - POST /api/v1/categories — admin create category
    - GET /api/v1/categories/{slug}/products — products by category including subcategories
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.6, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 3.4 Implement Catalog Service product import management command
    - Create `seed_products` management command that fetches from DummyJSON API
    - Map DummyJSON fields: title→name, thumbnail→primary image, images→additional images, price, stock, category, brand, description
    - Handle duplicate SKU by updating existing product (idempotent)
    - Accept --limit parameter (1-194, default 30)
    - Handle DummyJSON API unreachable gracefully with error message
    - _Requirements: 4.6, 4.7, 4.8, 24.1, 24.6, 24.7, 24.8_

  - [ ]* 3.5 Write unit tests for Catalog Service
    - Test model constraints (price range, stock range, slug uniqueness, category level enforcement)
    - Test serializer validation (missing fields, invalid ranges, duplicate SKU)
    - Test API endpoints (list, detail, search, filter, sort, pagination, admin CRUD)
    - Test product import command (success, API failure, duplicate handling)
    - Test permissions (admin-only endpoints reject customer/guest)
    - _Requirements: 4.1, 4.2, 5.1, 5.6, 5.7, 5.8, 6.3, 6.4_

  - [x] 3.6 Implement Frontend homepage and product listing
    - Create homepage with hero section, category shortcuts (8 categories), featured products grid (4-8 products)
    - Create product listing page with sidebar filters (category, brand, price range, rating), sort options, paginated grid (12 per page)
    - Create product card component with image, name, price, rating, stock badge
    - Implement image fallback placeholder for failed image loads
    - Implement skeleton loading placeholders while API requests are pending
    - Implement empty state and error state with retry
    - _Requirements: 22.1, 22.2, 22.9, 22.10_

  - [x] 3.7 Implement Frontend product detail page
    - Create product detail page with image gallery, specifications, price, stock status, add-to-cart button
    - Display average rating and review count
    - Implement responsive layout (2-col/1-col below 768px)
    - _Requirements: 22.3, 22.11_

- [x] 4. Checkpoint — Catalog service end-to-end
  - Seed products via management command, verify homepage displays 50+ products with images
  - Verify product detail page opens, filter by category works
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Phase 2 — Identity Service (Authentication & Authorization)
  - [x] 5.1 Implement Identity Service models and migrations
    - Create User model with UUID PK, email (unique, max 254), password_hash, role (admin/staff/customer), is_active, failed_login_attempts, locked_until, timestamps
    - Create RefreshToken model with UUID PK, user FK, token_hash (unique), expires_at, is_revoked, created_at
    - Configure MySQL database connection
    - Generate and apply migrations
    - _Requirements: 1.1, 2.1, 2.5_

  - [x] 5.2 Implement Identity Service authentication endpoints
    - POST /api/v1/auth/register — create user with customer role, hash password, return access + refresh tokens
    - POST /api/v1/auth/login — validate credentials, return access (15min) + refresh (7d) tokens, include user_id/role/issuer/exp in JWT payload
    - POST /api/v1/auth/refresh — validate refresh token, issue new token pair, invalidate old refresh token
    - Implement account lockout: 5 failed attempts in 15 minutes → lock for 15 minutes
    - Validate email format and password length (8-128 chars)
    - Return generic UNAUTHORIZED on invalid credentials (don't reveal which field is wrong)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 25.7_

  - [x] 5.3 Implement JWT validation middleware for all services
    - Create shared JWT validation logic using public key (no callback to Identity Service)
    - Extract user_id and role from token claims
    - Return 401 UNAUTHORIZED for missing/expired/malformed/invalid-signature tokens
    - Allow unauthenticated access to public endpoints (product list, product detail, categories)
    - _Requirements: 3.1, 3.4, 3.5, 3.6, 3.7_

  - [ ]* 5.4 Write unit tests for Identity Service
    - Test registration (success, duplicate email, invalid email, short/long password)
    - Test login (success, wrong password, wrong email, locked account)
    - Test refresh token (success, expired, revoked, invalid)
    - Test JWT validation middleware (valid token, expired, malformed, missing)
    - Test RBAC permissions (admin, staff, customer, guest access patterns)
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.6, 3.2, 3.3, 3.4_

  - [x] 5.5 Implement Frontend authentication flow
    - Create login page with email/password form
    - Create registration page
    - Implement token storage, auto-refresh, and logout
    - Add auth state to API client (inject Authorization header)
    - Protect cart/checkout/order routes for authenticated users
    - _Requirements: 22.5, 22.6_

- [x] 6. Phase 2 — Cart Service
  - [x] 6.1 Implement Cart Service models and migrations
    - Create Cart model with UUID PK, user_id (unique — one cart per customer), timestamps
    - Create CartItem model with UUID PK, cart FK, product_id, quantity (1-99), timestamps; unique constraint on (cart_id, product_id)
    - Generate and apply migrations
    - _Requirements: 7.8_

  - [x] 6.2 Implement Cart Service endpoints
    - GET /api/v1/cart/current — return cart items with product_id, name, thumbnail, unit_price, quantity, line_total, cart subtotal
    - POST /api/v1/cart/items — add item; validate product active + in-stock via Catalog Service (ServiceClient, 3s timeout)
    - PATCH /api/v1/cart/items/{id} — update quantity (1-99, validate stock)
    - DELETE /api/v1/cart/items/{id} — remove item, return updated cart
    - Enforce one cart per authenticated customer (user_id from JWT)
    - Return PRODUCT_OUT_OF_STOCK if product inactive or insufficient stock
    - Return SERVICE_UNAVAILABLE if Catalog Service unreachable
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_

  - [ ]* 6.3 Write unit tests for Cart Service
    - Test add item (success, out of stock, inactive product, catalog unavailable)
    - Test update quantity (valid, exceeds stock, below 1, above 99)
    - Test remove item
    - Test one cart per customer constraint
    - Test ServiceClient timeout handling
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_

  - [ ]* 6.4 Write property test for Cart-Product Consistency
    - **Property 3: Cart-Product Consistency**
    - Verify that CartItem can only reference active, in-stock products at time of addition
    - **Validates: Requirements 7.1, 7.2**

  - [ ]* 6.5 Write property test for One Cart Per Customer
    - **Property 4: One Cart Per Customer**
    - Verify unique constraint on Cart.user_id prevents multiple carts per customer
    - **Validates: Requirements 7.8**

  - [x] 6.6 Implement Frontend cart page
    - Create cart page with item list, quantity controls (+/-), remove button
    - Display order summary (subtotal, item count)
    - Add proceed-to-checkout button (disabled if cart empty)
    - Implement add-to-cart from product detail page
    - _Requirements: 22.5_

- [x] 7. Phase 2 — Order Service
  - [x] 7.1 Implement Order Service models and migrations
    - Create Order model with UUID PK, user_id, status (enum: created/payment_pending/paid/payment_failed/shipping/completed/cancelled), subtotal, shipping_fee, discount_amount, total_amount (all Decimal 2dp), shipping_address, timestamps
    - Create OrderItem model with UUID PK, order FK, product_id, product_name, product_sku, product_image_url, unit_price, quantity, line_total (price snapshot fields)
    - Create OrderStatusHistory model with UUID PK, order FK, from_status, to_status, reason (max 500), created_at
    - Define ORDER_TRANSITIONS dict for allowed state transitions
    - Generate and apply migrations
    - _Requirements: 8.2, 8.5, 8.6, 23.1, 23.2, 23.3_

  - [x] 7.2 Implement Order Service checkout workflow
    - POST /api/v1/orders/checkout — orchestrate: get cart (5s timeout) → validate items via Catalog (5s timeout) → create order + items with price snapshot → create payment via Payment Service → handle payment result → create shipment on success
    - Implement status transition logic with optimistic locking (WHERE current_status = expected)
    - Reject empty cart checkout with VALIDATION_ERROR
    - Reject non-customer roles with FORBIDDEN
    - Return SERVICE_UNAVAILABLE if Cart/Catalog unavailable within 5s
    - Return VALIDATION_ERROR listing failed items if any product validation fails
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 23.4, 23.5_

  - [x] 7.3 Implement Order Service list and detail endpoints
    - GET /api/v1/orders — paginated list of user's orders (customer sees own, staff/admin see all)
    - GET /api/v1/orders/{id} — order detail with items and status history
    - PATCH /api/v1/orders/{id}/cancel — cancel order (customer owner, staff, or admin only)
    - Enforce ownership check: customer can only view/cancel own orders
    - _Requirements: 23.2, 23.3, 23.6, 25.4_

  - [ ]* 7.4 Write unit tests for Order Service
    - Test checkout (success, empty cart, cart unavailable, product validation failure, non-customer)
    - Test status transitions (valid transitions, invalid transitions, concurrent transition rejection)
    - Test price snapshot immutability
    - Test order total calculation
    - Test ownership enforcement
    - _Requirements: 8.1, 8.3, 8.4, 8.7, 8.8, 23.2, 23.4, 23.5_

  - [ ]* 7.5 Write property test for Price Snapshot Immutability
    - **Property 1: Price Snapshot Immutability**
    - Verify OrderItem unit_price, product_name, product_sku, product_image_url never change after creation
    - **Validates: Requirements 8.2**

  - [ ]* 7.6 Write property test for Order Status Transition Validity
    - **Property 2: Order Status Transition Validity**
    - Verify only allowed transitions succeed; invalid transitions are rejected atomically
    - **Validates: Requirements 23.2, 23.4**

- [x] 8. Phase 2 — Payment Service
  - [x] 8.1 Implement Payment Service models and migrations
    - Create PaymentTransaction model with UUID PK, order_id, amount (Decimal 2dp), status (pending/success/failed), idempotency_key (unique), timestamps
    - Create PaymentStatusHistory model with UUID PK, transaction FK, from_status, to_status, created_at
    - Configure MySQL database connection
    - Generate and apply migrations
    - _Requirements: 9.1, 9.6_

  - [x] 8.2 Implement Payment Service endpoints
    - POST /api/v1/payments — create payment transaction (order_id, amount, idempotency_key required); return existing result if idempotency_key matches
    - POST /api/v1/payments/{id}/simulate-success — transition pending→success, record status history
    - POST /api/v1/payments/{id}/simulate-failure — transition pending→failed, record status history
    - Validate required fields (order_id, amount, idempotency_key)
    - Record PaymentStatusHistory for every transition
    - _Requirements: 9.1, 9.2, 9.3, 9.6, 9.7, 9.8_

  - [ ]* 8.3 Write unit tests for Payment Service
    - Test create payment (success, missing fields, idempotency duplicate)
    - Test simulate success/failure transitions
    - Test status history recording
    - _Requirements: 9.1, 9.2, 9.3, 9.6, 9.7, 9.8_

  - [ ]* 8.4 Write property test for Payment Idempotency
    - **Property 6: Payment Idempotency**
    - Verify duplicate payment requests with same idempotency_key return same result without creating additional transactions
    - **Validates: Requirements 9.6**

- [x] 9. Phase 2 — Shipping Service
  - [x] 9.1 Implement Shipping Service models and migrations
    - Create Shipment model with UUID PK, order_id (unique), tracking_code (unique, 8-20 alphanumeric), status (processing/shipping/delivered), shipping_address, timestamps
    - Create ShipmentStatusHistory model with UUID PK, shipment FK, from_status, to_status, created_at
    - Define SHIPMENT_TRANSITIONS: processing→shipping, shipping→delivered (forward-only)
    - Generate and apply migrations
    - _Requirements: 10.2, 10.3_

  - [x] 9.2 Implement Shipping Service endpoints
    - POST /api/v1/shipments — create shipment with generated tracking code, initial status "processing"
    - PATCH /api/v1/shipments/{id}/status — staff updates status (forward-only transitions enforced)
    - GET /api/v1/shipments/order/{order_id} — customer gets shipment status, tracking code, status history
    - Enforce ownership: customer can only view own order's shipment (FORBIDDEN otherwise)
    - Reject invalid transitions with VALIDATION_ERROR
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.7_

  - [ ]* 9.3 Write unit tests for Shipping Service
    - Test create shipment (success, tracking code generation)
    - Test status transitions (valid forward, invalid backward)
    - Test ownership enforcement
    - _Requirements: 10.2, 10.3, 10.4, 10.5, 10.7_

  - [ ]* 9.4 Write property test for Shipment Status Forward-Only
    - **Property 7: Shipment Status Forward-Only**
    - Verify shipment status only transitions forward: processing→shipping→delivered; backward transitions rejected
    - **Validates: Requirements 10.3, 10.5**

- [x] 10. Checkpoint — Full purchase journey
  - Verify end-to-end: register → login → browse → add to cart → checkout → payment success → shipment created
  - Verify payment failure path: order status becomes payment_failed
  - Verify shipping retry logic (Order Service retries 3x with 2s interval)
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Phase 2 — Frontend Checkout and Order Tracking
  - [x] 11.1 Implement Frontend checkout page
    - Create checkout page with shipping address form, payment method selector, order summary
    - Call POST /api/orders/checkout on submit
    - Display payment status feedback (success/failure)
    - Redirect to order confirmation on success
    - _Requirements: 22.6_

  - [x] 11.2 Implement Frontend order tracking page
    - Create order tracking page with status timeline (created → payment_pending → paid → shipping → delivered)
    - Display items purchased with price snapshot data
    - Display shipping details and tracking code
    - _Requirements: 22.7_

- [x] 12. Phase 3 — AI Service Setup and RAG Chatbot
  - [x] 12.1 Create AI Service scaffold (FastAPI)
    - Initialize FastAPI project structure: app/main.py, app/api/, app/core/, app/application/, app/infrastructure/, app/ml/
    - Implement core config, structured logging, error handling matching standard envelope format
    - Implement catalog_client.py using ServiceClient pattern (validate products against Catalog Service)
    - Create Dockerfile (Python 3.11, uvicorn)
    - Configure PostgreSQL + pgvector connection
    - Add healthcheck endpoints (GET /healthz, GET /readyz)
    - _Requirements: 20.1, 20.2, 19.1, 19.2_

  - [x] 12.2 Implement AI Service data models and migrations
    - Create EmbeddingDocument model (UUID PK, source_type, source_id, title, content, embedding vector(768), metadata JSON, timestamps)
    - Create ChatLog model (UUID PK, user_id nullable, session_id, message, response, recommended_product_ids JSON, grounded bool, hallucination_risk, created_at)
    - Create UserInteraction model (UUID PK, user_id, product_id, event_type, timestamp)
    - Create RecommendationLog model (UUID PK, user_id, context_product_id, recommended_product_ids JSON, scores JSON, created_at)
    - Apply migrations with pgvector extension enabled
    - _Requirements: 12.6_

  - [x] 12.3 Implement RAG ingestion pipeline
    - Create management command to export catalog products as embedding documents (title + description + brand + category + price + attributes)
    - Create management command to ingest TechShop FAQ/policy documents (warranty, shipping, return, payment policies)
    - Normalize text, chunk documents, generate embeddings (sentence-transformers or similar)
    - Store embeddings in ai_db using pgvector
    - Report total documents embedded on completion
    - Handle idempotent re-ingestion (skip existing, update changed)
    - _Requirements: 12.6, 24.5, 24.7, 24.8_

  - [x] 12.4 Implement RAG chat endpoint
    - POST /api/v1/chat — accept message (1-1000 chars), user_id (optional), context (current_product_id, cart_product_ids)
    - Retrieve top-5 relevant documents by cosine similarity from pgvector
    - If no document exceeds 0.5 similarity score, return AI_NO_CONTEXT_FOUND error
    - Generate grounded answer using LLM client
    - Validate recommended product IDs against Catalog Service (active + in-stock)
    - Return answer, recommended_product_ids, retrieved_documents with scores, safety metadata (grounded flag, hallucination_risk)
    - Enforce 5-second response timeout
    - Allow guest users (limit 10 queries per session)
    - Validate message length (empty or >1000 chars → VALIDATION_ERROR)
    - Log chat interaction to ChatLog
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.7, 12.8_

  - [ ]* 12.5 Write unit tests for RAG chatbot
    - Test chat endpoint (valid query, empty message, too-long message)
    - Test similarity threshold (no context found scenario)
    - Test product validation (exclude inactive/out-of-stock from recommendations)
    - Test guest rate limiting (10 queries per session)
    - _Requirements: 12.1, 12.3, 12.7, 12.8_

  - [x] 12.6 Implement Frontend AI chatbot interface
    - Create AI chatbot drawer/full-page component
    - Display 3-5 suggested prompts for new conversations
    - Render chat bubbles distinguishing user messages from AI responses
    - Render up to 5 embedded product recommendation cards within AI responses
    - Integrate chatbot access from product detail page
    - Handle loading state and error state
    - _Requirements: 22.4_

- [x] 13. Checkpoint — RAG chatbot working
  - Ingest catalog + FAQ documents, verify embeddings stored
  - Ask product advisory question, verify grounded answer with product IDs
  - Verify frontend renders product cards in chat response
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Phase 4 — AI Sentiment Analysis Model
  - [x] 14.1 Implement sentiment analysis model and endpoint
    - Create sentiment model module (BERT/PhoBERT/mBERT) in app/ml/sentiment/
    - Implement model loading, tokenization, and inference pipeline
    - POST /api/v1/sentiment — accept review text, return label (positive/neutral/negative), confidence score (0.0-1.0), model_version
    - Validate input: reject empty, whitespace-only, or >5000 chars with VALIDATION_ERROR
    - Enforce 3-second response timeout
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

  - [x] 14.2 Implement dataset ingestion for sentiment training
    - Create management command to ingest Amazon Reviews 2023/UCSD dataset
    - Parse review records, store processed entries for training
    - Report total records ingested on completion
    - Handle missing source file gracefully (non-zero exit + error message)
    - Idempotent: skip duplicate records
    - _Requirements: 24.2, 24.6, 24.7, 24.8_

  - [ ]* 14.3 Write unit tests for sentiment analysis
    - Test endpoint (valid text, empty text, too-long text)
    - Test model returns valid label and score range
    - Test model_version included in response
    - _Requirements: 14.1, 14.3, 14.4_

- [x] 15. Phase 4 — AI Customer Segmentation Model
  - [x] 15.1 Implement customer segmentation model and endpoint
    - Create KMeans segmentation module in app/ml/segmentation/
    - Implement RFM feature computation (Recency days, Frequency orders, Monetary total spend)
    - Implement KMeans clustering with silhouette score optimization (3-8 clusters)
    - POST /api/v1/segmentation/run — admin triggers segmentation
    - Return segment assignments with segment_id, segment_name (descriptive labels), RFM values
    - Store results in CustomerSegment and SegmentationRun tables
    - Return total customers segmented, clusters created, silhouette score
    - Reject if fewer than 30 customers with completed orders (VALIDATION_ERROR)
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

  - [x] 15.2 Implement dataset ingestion for segmentation training
    - Create management command to ingest UCI Online Retail dataset
    - Parse transaction records, store processed entries for RFM analysis
    - Report total customer records processed on completion
    - Handle missing source file gracefully
    - Idempotent: skip duplicate records
    - _Requirements: 24.4, 24.6, 24.7, 24.8_

  - [ ]* 15.3 Write unit tests for customer segmentation
    - Test RFM computation correctness
    - Test cluster count optimization
    - Test insufficient data rejection (<30 customers)
    - Test result storage
    - _Requirements: 15.1, 15.4, 15.5_

- [x] 16. Phase 4 — AI Product Classification Model
  - [x] 16.1 Implement product classification model and endpoint
    - Create XGBoost/LightGBM classification module in app/ml/product_classifier/
    - Implement feature extraction from product title, description, brand, attributes
    - POST /api/v1/classification — accept product data, return predicted category_label, category_id, confidence_score (0.0-1.0)
    - Auto-assign category if confidence >= 0.5; set status to review_needed if < 0.5
    - Return VALIDATION_ERROR if model unavailable or title+description both empty
    - Store results in ProductClassification table
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

  - [ ]* 16.2 Write unit tests for product classification
    - Test classification endpoint (valid product, empty title+description)
    - Test confidence threshold logic (auto-assign vs review_needed)
    - Test model unavailable handling
    - _Requirements: 16.1, 16.3, 16.4, 16.5_

- [x] 17. Phase 4 — AI Sequence Recommendation Model
  - [x] 17.1 Implement sequence recommendation model and endpoint
    - Create LSTM/GRU sequence model module in app/ml/sequence_model/
    - Implement model that predicts next products from interaction sequence
    - Integrate into GET /api/v1/recommendations endpoint as sequence_score component (weight 0.30)
    - Require minimum 2 product interactions; return VALIDATION_ERROR if fewer
    - Return at most 10 candidate product IDs with probability scores (0.0-1.0)
    - Exclude inactive and out-of-stock products from results
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_

  - [x] 17.2 Implement dataset ingestion for sequence model training
    - Create management command to ingest RetailRocket Ecommerce Dataset
    - Parse user interaction events (view, add_to_cart, purchase)
    - Store processed sequences for training
    - Report total sequences generated on completion
    - Handle missing source file gracefully
    - Idempotent: skip duplicate records
    - _Requirements: 24.3, 24.6, 24.7, 24.8_

  - [ ]* 17.3 Write unit tests for sequence recommendation
    - Test with valid interaction sequence (>=2 interactions)
    - Test with insufficient interactions (<2)
    - Test exclusion of inactive/out-of-stock products
    - Test score range (0.0-1.0)
    - _Requirements: 17.1, 17.3, 17.4, 17.5_

- [x] 18. Phase 4 — Hybrid Recommendation Endpoint
  - [x] 18.1 Implement hybrid recommendation scoring pipeline
    - GET /api/v1/recommendations — accept user_id, optional context_product_id, optional budget (min/max price)
    - Compute hybrid score: 0.30 sequence + 0.25 content similarity + 0.20 collaborative + 0.15 popularity + 0.10 business rules
    - Cold start fallback: if user has <3 interactions, use popularity + business rules only
    - Apply filters: exclude inactive, exclude out-of-stock, exclude cart items (unless complementary/accessory), apply budget constraint
    - Return top 10 products with scores and reason labels
    - Respond within 1 second
    - Return SERVICE_UNAVAILABLE if model unavailable
    - Log recommendations to RecommendationLog
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8_

  - [ ]* 18.2 Write unit tests for hybrid recommendations
    - Test full hybrid scoring (user with >=3 interactions)
    - Test cold start fallback (<3 interactions)
    - Test budget filtering
    - Test cart item exclusion logic
    - Test inactive/out-of-stock exclusion
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

  - [x] 18.3 Implement Frontend AI recommendation carousel
    - Add recommendation carousel to homepage (up to 10 products)
    - Fetch recommendations from /api/ai/recommendations
    - Display product cards with score-based ordering
    - _Requirements: 22.1_

- [x] 19. Checkpoint — All AI models functional
  - Verify sentiment analysis returns valid labels for sample reviews
  - Verify segmentation produces clusters with silhouette score
  - Verify classification assigns categories with confidence scores
  - Verify sequence model predicts next products
  - Verify hybrid recommendations combine all scores correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 20. Phase 5 — Review Service
  - [x] 20.1 Implement Review Service models and migrations
    - Create Review model with UUID PK, user_id, product_id, rating (1-5), comment (1-2000 chars), sentiment_label (nullable), sentiment_score (nullable), sentiment_status (completed/pending), created_at
    - Add unique constraint on (user_id, product_id)
    - Generate and apply migrations
    - _Requirements: 11.1, 11.3_

  - [x] 20.2 Implement Review Service endpoints
    - POST /api/v1/reviews — create review; verify purchase via Order Service (completed order containing product); call AI sentiment endpoint; store sentiment or mark pending if AI unavailable
    - GET /api/v1/reviews/product/{product_id} — paginated list sorted by newest, default page_size 10, max 50; include rating, comment, sentiment_label, timestamp
    - Calculate and expose average rating (1 decimal) and total review count per product
    - Reject duplicate review (same user + product) with CONFLICT
    - Reject review for unpurchased product with FORBIDDEN
    - Handle AI Service unavailable gracefully (store review, mark sentiment_status=pending)
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

  - [ ]* 20.3 Write unit tests for Review Service
    - Test create review (success, duplicate, unpurchased product, AI unavailable)
    - Test list reviews (pagination, sorting)
    - Test average rating calculation
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

  - [ ]* 20.4 Write property test for One Review Per Customer Per Product
    - **Property 5: One Review Per Customer Per Product**
    - Verify unique constraint on (user_id, product_id) prevents duplicate reviews
    - **Validates: Requirements 11.3**

- [x] 21. Phase 5 — Admin Dashboard
  - [x] 21.1 Implement Frontend admin dashboard
    - Create admin dashboard with overview metrics (total products, orders, revenue, active users)
    - Create product management table (list, edit, import trigger)
    - Create order management table (list, status updates)
    - Create AI model status cards (sentiment model version, segmentation last run, classification stats)
    - Restrict access to admin role
    - _Requirements: 22.8_

  - [x] 21.2 Implement admin-specific API endpoints across services
    - Catalog: GET /api/v1/admin/stats (product counts, category counts)
    - Order: GET /api/v1/admin/stats (order counts by status, revenue totals)
    - Identity: GET /api/v1/admin/users (user list with roles, paginated)
    - AI: GET /api/v1/admin/models (model status, last run timestamps)
    - Enforce admin role on all admin endpoints
    - _Requirements: 3.1, 25.3_

- [x] 22. Phase 5 — Security Hardening and CORS
  - [x] 22.1 Implement security configurations across all services
    - Configure CORS to allow only known frontend origin
    - Set DEBUG=false in deployment configuration
    - Ensure .env files excluded from version control
    - Verify admin endpoints require admin role, staff endpoints require staff/admin
    - Verify customer resource ownership checks (cart, order, review)
    - Verify gateway body size limit (20MB)
    - _Requirements: 25.1, 25.2, 25.3, 25.4, 25.5, 25.6_

- [x] 23. Phase 5 — Integration Wiring and Final Polish
  - [x] 23.1 Wire Order Service retry logic for Shipping Service
    - Implement retry on shipment creation: 3 attempts, 2-second interval
    - Order remains in "paid" status if all retries fail
    - Log each retry attempt with request_id
    - _Requirements: 10.6_

  - [x] 23.2 Wire Review Service sentiment integration
    - On review creation, call AI /api/v1/sentiment endpoint
    - Store sentiment_label and sentiment_score on success
    - Mark sentiment_status=pending on AI failure (graceful degradation)
    - _Requirements: 11.4, 11.5_

  - [x] 23.3 Wire Catalog rating updates from Review Service
    - After review creation, update product rating_avg and rating_count in Catalog Service
    - Use ServiceClient to call Catalog update endpoint
    - _Requirements: 11.7_

  - [ ]* 23.4 Write property test for Database Isolation
    - **Property 8: Database Isolation**
    - Verify no service directly accesses another service's database; all cross-service access via REST
    - Validate Docker network configuration enforces isolation
    - **Validates: Requirements 18.4**

  - [ ]* 23.5 Write integration tests for checkout flow
    - Test full checkout: cart → order → payment → shipping (mock downstream services)
    - Test review with sentiment: review → AI sentiment endpoint
    - Test cart stock validation: cart → catalog product validation
    - _Requirements: 8.1, 9.4, 10.1, 11.4_

- [x] 24. Final Checkpoint — Full system demo
  - Verify complete demo script: homepage → search → detail → AI chat → cart → checkout → payment → shipping → order tracking → admin dashboard
  - Verify all healthchecks pass
  - Verify structured logging with request_id propagation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at each phase boundary
- Property tests validate universal correctness properties defined in the design document
- Unit tests validate specific examples and edge cases
- The shared core app (task 1.3) is reused across all Django services — implement once, copy to each service
- AI models can use pre-trained weights for demo; full training is documented in datasets/README.md
- Frontend tasks can be parallelized with backend tasks once API contracts are defined
- Inter-service communication always uses ServiceClient — never raw HTTP calls in business logic

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.4"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.6"] },
    { "id": 2, "tasks": ["1.5", "3.1", "5.1"] },
    { "id": 3, "tasks": ["3.2", "3.4", "5.2"] },
    { "id": 4, "tasks": ["3.3", "5.3", "5.5"] },
    { "id": 5, "tasks": ["3.5", "3.6", "5.4", "6.1", "8.1", "9.1"] },
    { "id": 6, "tasks": ["3.7", "6.2", "8.2", "9.2"] },
    { "id": 7, "tasks": ["6.3", "6.4", "6.5", "6.6", "8.3", "8.4", "9.3", "9.4"] },
    { "id": 8, "tasks": ["7.1"] },
    { "id": 9, "tasks": ["7.2", "7.3"] },
    { "id": 10, "tasks": ["7.4", "7.5", "7.6", "11.1", "11.2"] },
    { "id": 11, "tasks": ["12.1"] },
    { "id": 12, "tasks": ["12.2", "12.3"] },
    { "id": 13, "tasks": ["12.4", "12.6"] },
    { "id": 14, "tasks": ["12.5", "14.1", "14.2", "15.1", "15.2", "16.1"] },
    { "id": 15, "tasks": ["14.3", "15.3", "16.2", "17.1", "17.2"] },
    { "id": 16, "tasks": ["17.3", "18.1"] },
    { "id": 17, "tasks": ["18.2", "18.3", "20.1"] },
    { "id": 18, "tasks": ["20.2", "20.3", "20.4"] },
    { "id": 19, "tasks": ["21.1", "21.2", "22.1"] },
    { "id": 20, "tasks": ["23.1", "23.2", "23.3"] },
    { "id": 21, "tasks": ["23.4", "23.5"] }
  ]
}
```
