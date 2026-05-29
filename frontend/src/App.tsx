import React, { useState, useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { PRODUCTS } from "./products";
import { Product, CartItem } from "./types";
import Navbar from "./components/Navbar";
import ProductCard from "./components/ProductCard";
import ProductDetails from "./components/ProductDetails";
import ComparisonModal from "./components/ComparisonModal";
import AIChatBot from "./components/AIChatBot";
import Cart from "./components/Cart";
import Favorites from "./components/Favorites";
import LoginPage from "./components/auth/LoginPage";
import RegisterPage from "./components/auth/RegisterPage";
import ProtectedRoute from "./components/auth/ProtectedRoute";
import HomePage from "@frontend/src/pages/HomePage";
import ProductListingPage from "@frontend/src/pages/ProductListingPage";
import ProductDetailPage from "@frontend/src/pages/ProductDetailPage";
import { Search, Sparkles, Scale, ShoppingBag, ShieldCheck, RefreshCw, AlertCircle, HelpCircle } from "lucide-react";

export default function App() {
  const [activeCategory, setActiveCategory] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [cart, setCart] = useState<CartItem[]>([]);
  const [comparedProducts, setComparedProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  // UI drawers open triggers
  const [cartOpen, setCartOpen] = useState(false);
  const [comparisonOpen, setComparisonOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [favoritesOpen, setFavoritesOpen] = useState(false);

  // Wishlist/Favorites lists
  const [favorites, setFavorites] = useState<Product[]>([]);

  // AI Semantic search intelligence references
  const [aiSearchPrompt, setAiSearchPrompt] = useState("");
  const [aiSearching, setAiSearching] = useState(false);
  const [aiSearchError, setAiSearchError] = useState<string | null>(null);

  // Initialize cart and favorites from localStorage if exists
  useEffect(() => {
    try {
      const storedCart = localStorage.getItem("aether_cart");
      if (storedCart) {
        setCart(JSON.parse(storedCart));
      }
      const storedFav = localStorage.getItem("aether_favorites");
      if (storedFav) {
        setFavorites(JSON.parse(storedFav));
      }
    } catch (e) {
      console.error("Local storage sync bypassed:", e);
    }
  }, []);

  // Save cart to local storage on updates
  const saveCart = (newCart: CartItem[]) => {
    setCart(newCart);
    try {
      localStorage.setItem("aether_cart", JSON.stringify(newCart));
    } catch (e) {
      console.warn("Local storage capacity limit:", e);
    }
  };

  const handleAddToCart = (product: Product) => {
    const existingIdx = cart.findIndex((item) => item.product.id === product.id);
    let updatedCart: CartItem[] = [];

    if (existingIdx > -1) {
      updatedCart = [...cart];
      updatedCart[existingIdx].quantity += 1;
    } else {
      updatedCart = [...cart, { product, quantity: 1 }];
    }

    saveCart(updatedCart);
    setCartOpen(true); // Open drawer on addition
  };

  const handleUpdateQuantity = (productId: string, delta: number) => {
    const updated = cart
      .map((item) => {
        if (item.product.id === productId) {
          return { ...item, quantity: Math.max(1, item.quantity + delta) };
        }
        return item;
      })
      .filter((item) => item.quantity > 0);
    saveCart(updated);
  };

  const handleRemoveItem = (productId: string) => {
    const updated = cart.filter((item) => item.product.id !== productId);
    saveCart(updated);
  };

  const handleClearCart = () => {
    saveCart([]);
  };

  const saveFavorites = (newFavorites: Product[]) => {
    setFavorites(newFavorites);
    try {
      localStorage.setItem("aether_favorites", JSON.stringify(newFavorites));
    } catch (e) {
      console.warn("Local storage favorites limit:", e);
    }
  };

  const handleToggleFavorite = (product: Product) => {
    const exists = favorites.some((p) => p.id === product.id);
    let updated: Product[] = [];
    if (exists) {
      updated = favorites.filter((p) => p.id !== product.id);
    } else {
      updated = [...favorites, product];
    }
    saveFavorites(updated);
  };

  // Toggle products on comparison board (cap at 2 products for high fidelity reports)
  const handleToggleCompare = (product: Product) => {
    setComparedProducts((prev) => {
      const exists = prev.some((p) => p.id === product.id);
      if (exists) {
        return prev.filter((p) => p.id !== product.id);
      } else {
        if (prev.length >= 2) {
          // If already 2 products, wrap-around remove first and add new or warn
          return [prev[1], product];
        }
        return [...prev, product];
      }
    });

    // Toggle comparison drawer visible so they see their selection
    setComparisonOpen(true);
  };

  const handleRemoveCompare = (product: Product) => {
    setComparedProducts((prev) => prev.filter((p) => p.id !== product.id));
  };

  // Action semantic search using local or remote Gemini API recommendation!
  const handleAISemanticSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const prompt = aiSearchPrompt.trim();
    if (!prompt) return;

    setAiSearching(true);
    setAiSearchError(null);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          messages: [
            {
              sender: "user",
              text: `Search query: "${prompt}". Match this description to exactly ONE corresponding ID of the stock items listed in catalog. Reply ONLY with the matched product ID lowercase among: ar-spectacles, anc-headphones, titanium-smartwatch, mech-keyboard, smart-projector, ergonomic-trackpad. If absolutely none matches, reply with 'none'. Do not say anything else.`
            }
          ]
        })
      });

      const data = await res.json();
      if (res.ok && data.text) {
        const cleanedId = data.text.trim().toLowerCase();

        // Find corresponding product
        const matched = PRODUCTS.find((p) => cleanedId.includes(p.id) || p.id.includes(cleanedId));
        if (matched) {
          setSelectedProduct(matched);
          setAiSearchPrompt("");
        } else {
          setAiSearchError("I couldn't pinpoint a perfect product match for that description. Try asking our floating shopping counselor!");
        }
      } else {
        throw new Error(data.error || "Failed to parse index recommendation");
      }
    } catch (err: any) {
      console.error(err);

      // Smart local fallback regex lookup for client-side matching if backend or key is offline
      const lowerPrompt = prompt.toLowerCase();
      let fallbackProduct: Product | null = null;

      if (lowerPrompt.includes("ar") || lowerPrompt.includes("glass") || lowerPrompt.includes("wearable") || lowerPrompt.includes("lens") || lowerPrompt.includes("translate")) {
        fallbackProduct = PRODUCTS.find((p) => p.id === "ar-spectacles") || null;
      } else if (lowerPrompt.includes("headphone") || lowerPrompt.includes("anc") || lowerPrompt.includes("audio") || lowerPrompt.includes("noise") || lowerPrompt.includes("sound")) {
        fallbackProduct = PRODUCTS.find((p) => p.id === "anc-headphones") || null;
      } else if (lowerPrompt.includes("watch") || lowerPrompt.includes("chrono") || lowerPrompt.includes("gps") || lowerPrompt.includes("health") || lowerPrompt.includes("pulse")) {
        fallbackProduct = PRODUCTS.find((p) => p.id === "titanium-smartwatch") || null;
      } else if (lowerPrompt.includes("key") || lowerPrompt.includes("board") || lowerPrompt.includes("mech") || lowerPrompt.includes("type") || lowerPrompt.includes("switch")) {
        fallbackProduct = PRODUCTS.find((p) => p.id === "mech-keyboard") || null;
      } else if (lowerPrompt.includes("projector") || lowerPrompt.includes("beam") || lowerPrompt.includes("aura") || lowerPrompt.includes("wall") || lowerPrompt.includes("laser")) {
        fallbackProduct = PRODUCTS.find((p) => p.id === "smart-projector") || null;
      } else if (lowerPrompt.includes("touch") || lowerPrompt.includes("trackpad") || lowerPrompt.includes("pad") || lowerPrompt.includes("wrist") || lowerPrompt.includes("ergonomic")) {
        fallbackProduct = PRODUCTS.find((p) => p.id === "ergonomic-trackpad") || null;
      }

      if (fallbackProduct) {
        setSelectedProduct(fallbackProduct);
        setAiSearchPrompt("");
      } else {
        setAiSearchError("Unable to locate. Try simpler tech queries like 'noise noise cancelling headphones' or 'wrist trackpad'.");
      }
    } finally {
      setAiSearching(false);
    }
  };

  // Filter products by search text and active category
  const filteredProducts = PRODUCTS.filter((product) => {
    const matchesCategory = activeCategory === "All" || product.category === activeCategory;
    const matchesKeyword =
      product.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      product.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      product.category.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesCategory && matchesKeyword;
  });

  const categories = ["All", "Wearables", "Audio", "Peripherals", "Home Tech"];

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/" element={
        <div className="min-h-screen bg-gray-50 text-gray-900 relative pb-16">
          <Navbar
            cartCount={cart.reduce((sum, i) => sum + i.quantity, 0)}
            onCartClick={() => setCartOpen(true)}
            comparedCount={comparedProducts.length}
            onCompareClick={() => setComparisonOpen(true)}
            onAICompanionClick={() => {
              const btn = document.getElementById("nav-ai-button");
              if (btn) btn.click();
            }}
            favoritesCount={favorites.length}
            onFavoritesClick={() => setFavoritesOpen(true)}
          />
          <main className="max-w-7xl mx-auto px-4 md:px-8 py-8 md:py-12">
            <HomePage />
          </main>
          {cartOpen && (
            <Cart items={cart} onUpdateQuantity={handleUpdateQuantity} onRemoveItem={handleRemoveItem} onClose={() => setCartOpen(false)} onClearCart={handleClearCart} />
          )}
          {selectedProduct && (
            <ProductDetails product={selectedProduct} onClose={() => setSelectedProduct(null)} onAddToCart={handleAddToCart} isFavorite={favorites.some((p) => p.id === selectedProduct.id)} onToggleFavorite={handleToggleFavorite} />
          )}
          {favoritesOpen && (
            <Favorites items={favorites} onRemoveFavorite={handleToggleFavorite} onAddToCart={handleAddToCart} onClose={() => setFavoritesOpen(false)} />
          )}
          {comparisonOpen && (
            <ComparisonModal products={comparedProducts} onRemove={handleRemoveCompare} onClose={() => setComparisonOpen(false)} allProducts={PRODUCTS} onSelectProduct={(p) => setComparedProducts((prev) => [...prev, p])} />
          )}
          <AIChatBot products={PRODUCTS} selectedProductId={selectedProduct?.id} />
        </div>
      } />
      <Route path="/products/:id" element={<ProductDetailPage />} />
      <Route path="/products" element={
        <div className="min-h-screen bg-gray-50 text-gray-900 relative pb-16">
          <Navbar
            cartCount={cart.reduce((sum, i) => sum + i.quantity, 0)}
            onCartClick={() => setCartOpen(true)}
            comparedCount={comparedProducts.length}
            onCompareClick={() => setComparisonOpen(true)}
            onAICompanionClick={() => {
              const btn = document.getElementById("nav-ai-button");
              if (btn) btn.click();
            }}
            favoritesCount={favorites.length}
            onFavoritesClick={() => setFavoritesOpen(true)}
          />
          <main className="max-w-7xl mx-auto px-4 md:px-8 py-6 md:py-10">
            <ProductListingPage />
          </main>
          {cartOpen && (
            <Cart items={cart} onUpdateQuantity={handleUpdateQuantity} onRemoveItem={handleRemoveItem} onClose={() => setCartOpen(false)} onClearCart={handleClearCart} />
          )}
          {selectedProduct && (
            <ProductDetails product={selectedProduct} onClose={() => setSelectedProduct(null)} onAddToCart={handleAddToCart} isFavorite={favorites.some((p) => p.id === selectedProduct.id)} onToggleFavorite={handleToggleFavorite} />
          )}
          {favoritesOpen && (
            <Favorites items={favorites} onRemoveFavorite={handleToggleFavorite} onAddToCart={handleAddToCart} onClose={() => setFavoritesOpen(false)} />
          )}
          {comparisonOpen && (
            <ComparisonModal products={comparedProducts} onRemove={handleRemoveCompare} onClose={() => setComparisonOpen(false)} allProducts={PRODUCTS} onSelectProduct={(p) => setComparedProducts((prev) => [...prev, p])} />
          )}
          <AIChatBot products={PRODUCTS} selectedProductId={selectedProduct?.id} />
        </div>
      } />
      <Route path="*" element={
        <div className="min-h-screen bg-editorial-bg text-editorial-text relative pb-16 selection:bg-editorial-accent selection:text-editorial-dark">

          {/* Decorative vertical editorial line and header reference */}
          <div className="border-t border-editorial-text/10" />

          {/* Navigation Headers */}
          <Navbar
            cartCount={cart.reduce((sum, i) => sum + i.quantity, 0)}
            onCartClick={() => setCartOpen(true)}
            comparedCount={comparedProducts.length}
            onCompareClick={() => setComparisonOpen(true)}
            onAICompanionClick={() => {
              // Trigger floating assistant open and notify
              const btn = document.getElementById("nav-ai-button");
              if (btn) btn.click();
            }}
            favoritesCount={favorites.length}
            onFavoritesClick={() => setFavoritesOpen(true)}
          />

          {/* Main Body Layout */}
          <main className="max-w-7xl mx-auto px-4 md:px-8 py-8 md:py-16 space-y-12">

            {/* HERO TITLE CONTAINER */}
            <section className="text-center max-w-4xl mx-auto space-y-5 animate-in fade-in slide-in-from-top-3 duration-500 pt-6">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 border border-editorial-text/15 bg-editorial-accent/20 text-editorial-text cap-text select-none">
                <Sparkles className="w-2.5 h-2.5 opacity-70" />
                <span>Issue No. 04 — Modernist Hardware</span>
              </div>

              <h1 className="serif text-4xl md:text-7xl font-bold text-editorial-text tracking-tighter leading-[0.95] py-2">
                Future Hardware,<br />
                <span className="serif italic text-editorial-text/75 font-normal">
                  Decided with AI Clarity.
                </span>
              </h1>

              <p className="text-xs md:text-sm text-editorial-text max-w-[585px] mx-auto leading-relaxed opacity-75 font-sans">
                An exploration of peak geometric precision and technical ingenuity. Compare premium catalog items side-by-side to authorize custom generative intelligence reviews immediately.
              </p>
            </section>

            {/* INTERACTIVE SEARCH & ADVISORY COMMAND CENTRE */}
            <section className="bg-editorial-paper border border-editorial-text/15 rounded-none p-6 md:p-8 max-w-4xl mx-auto space-y-6 animate-in fade-in duration-300">

              <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-end">

                {/* Command 1: Keyword matching search (5/12 cols) */}
                <div className="md:col-span-5 relative">
                  <label className="text-[9px] text-editorial-text font-bold uppercase tracking-wider font-mono mb-2 block">Keyword lookup</label>
                  <div className="relative">
                    <Search className="absolute left-3 top-3.5 w-3.5 h-3.5 text-editorial-text/45" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Query by keys, specs, or metrics..."
                      className="w-full text-xs bg-editorial-bg border border-editorial-text/20 focus:border-editorial-text focus:outline-none rounded-none pl-9 pr-3 py-3 transition-all duration-200 font-sans text-editorial-text"
                    />
                  </div>
                </div>

                {/* Command Divider or Connector */}
                <div className="hidden md:flex md:col-span-1 pb-3 justify-center text-[10px] font-mono text-editorial-text/50 uppercase tracking-widest font-semibold">
                  /
                </div>

                {/* Command 2: Generative Spec Search bar (6/12 cols) */}
                <form onSubmit={handleAISemanticSearch} className="md:col-span-6 relative font-sans">
                  <label className="text-[9px] text-editorial-text font-bold uppercase tracking-wider font-mono mb-2 block flex items-center justify-between">
                    <span>AI Intent Alignment</span>
                    <span className="text-[8px] tracking-normal font-mono opacity-50 font-normal">Cognitive match</span>
                  </label>

                  <div className="relative flex gap-2">
                    <input
                      type="text"
                      required
                      value={aiSearchPrompt}
                      onChange={(e) => setAiSearchPrompt(e.target.value)}
                      disabled={aiSearching}
                      placeholder="Describe goal: 'I want wrist relief writing spreadsheet code'..."
                      className="flex-grow text-xs bg-editorial-bg border border-editorial-text/25 focus:border-editorial-text focus:outline-none rounded-none pl-3.5 pr-10 py-3 transition-all duration-250 italic text-editorial-text"
                    />

                    <button
                      type="submit"
                      disabled={!aiSearchPrompt.trim() || aiSearching}
                      className="bg-editorial-text text-editorial-bg hover:bg-editorial-accent hover:text-editorial-text border border-editorial-text rounded-none px-4.5 flex items-center justify-center gap-1.5 shrink-0 transition-colors duration-250 disabled:opacity-40"
                    >
                      {aiSearching ? (
                        <RefreshCw className="w-3 h-3 animate-spin" />
                      ) : (
                        <>
                          <Sparkles className="w-3.5 h-3.5" />
                          <span className="text-[10px] font-bold uppercase tracking-wider font-mono hidden sm:inline">Search AI</span>
                        </>
                      )}
                    </button>
                  </div>
                </form>

              </div>

              {/* AI Search Assistant Notifications */}
              {aiSearchError && (
                <div className="p-3 bg-red-55/10 border border-red-500/20 text-red-900 text-xs rounded-none flex items-start gap-2.5 animate-in fade-in duration-200 font-mono">
                  <AlertCircle className="w-4 h-4 text-red-700 shrink-0 mt-0.5" />
                  <p>{aiSearchError}</p>
                </div>
              )}

            </section>

            {/* MAIN PRODUCT BROWSER GRID */}
            <section className="space-y-8 animate-in fade-in duration-300">

              {/* Categories Tab selector bar */}
              <div className="flex flex-wrap items-center justify-between gap-4 border-b border-editorial-text/15 pb-5">
                <div className="flex flex-wrap gap-2">
                  {categories.map((cat) => (
                    <button
                      key={cat}
                      onClick={() => setActiveCategory(cat)}
                      className={`text-[10px] uppercase tracking-wider py-2 px-4 rounded-none transition-all duration-250 cursor-pointer ${activeCategory === cat
                        ? "bg-editorial-text text-editorial-bg font-bold border border-editorial-text"
                        : "bg-transparent text-editorial-text/60 border border-editorial-text/10 hover:border-editorial-text/50 hover:text-editorial-text"
                        }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>

                <p className="text-[10px] text-editorial-text/50 font-mono tracking-widest uppercase">
                  Manifest — {filteredProducts.length} curations verified
                </p>
              </div>

              {/* Catalog grid */}
              {filteredProducts.length === 0 ? (
                <div className="bg-editorial-paper rounded-none border border-editorial-text/15 p-16 text-center space-y-5">
                  <Search className="w-8 h-8 text-editorial-text/30 mx-auto" />
                  <div className="space-y-2">
                    <p className="serif text-xl font-bold text-editorial-text">No corresponding devices located</p>
                    <p className="text-xs text-editorial-text/60 max-w-sm mx-auto font-sans leading-relaxed">
                      We could not pinpoint matching hardware items matching current indexing keywords in this collection.
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setSearchQuery("");
                      setActiveCategory("All");
                    }}
                    className="text-[10px] uppercase tracking-widest font-bold bg-editorial-text text-editorial-bg px-5 py-2.5 rounded-none border border-editorial-text hover:bg-transparent hover:text-editorial-text transition-colors duration-250 cursor-pointer"
                  >
                    Reset Layout filters
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
                  {filteredProducts.map((product) => (
                    <ProductCard
                      key={product.id}
                      product={product}
                      onViewDetails={setSelectedProduct}
                      onAddToCart={handleAddToCart}
                      isCompared={comparedProducts.some((p) => p.id === product.id)}
                      onToggleCompare={handleToggleCompare}
                      isFavorite={favorites.some((p) => p.id === product.id)}
                      onToggleFavorite={handleToggleFavorite}
                    />
                  ))}
                </div>
              )}

            </section>

          </main>

          {/* POPUP DRAWERS & MODALS OUTSIDE WORKSPACE */}

          {/* Shopping Basket Drawer */}
          {cartOpen && (
            <Cart
              items={cart}
              onUpdateQuantity={handleUpdateQuantity}
              onRemoveItem={handleRemoveItem}
              onClose={() => setCartOpen(false)}
              onClearCart={handleClearCart}
            />
          )}

          {/* Specifications Details Modal */}
          {selectedProduct && (
            <ProductDetails
              product={selectedProduct}
              onClose={() => setSelectedProduct(null)}
              onAddToCart={handleAddToCart}
              isFavorite={favorites.some((p) => p.id === selectedProduct.id)}
              onToggleFavorite={handleToggleFavorite}
            />
          )}

          {/* Wishlist / Saved Items Drawer */}
          {favoritesOpen && (
            <Favorites
              items={favorites}
              onRemoveFavorite={handleToggleFavorite}
              onAddToCart={(p) => {
                handleAddToCart(p);
              }}
              onClose={() => setFavoritesOpen(false)}
            />
          )}

          {/* Spec Comparisons matrix Modal */}
          {comparisonOpen && (
            <ComparisonModal
              products={comparedProducts}
              onRemove={handleRemoveCompare}
              onClose={() => setComparisonOpen(false)}
              allProducts={PRODUCTS}
              onSelectProduct={(p) => {
                setComparedProducts((prev) => [...prev, p]);
              }}
            />
          )}

          {/* FLOATING GENERAL CHATBOT COMPANION (AI expert, synced to catalogue lists) */}
          <AIChatBot
            products={PRODUCTS}
            selectedProductId={selectedProduct?.id}
          />

          {/* Continuous footer status */}
          <footer className="border-t border-editorial-text/15 py-8 text-center text-[9px] text-editorial-text/45 font-mono tracking-widest uppercase mt-16 space-y-2 max-w-5xl mx-auto">
            <div>THE ARCHIVE — CURATED INTELLECTUAL HARDWARE FOR CONTEMPORARY DESIGNS</div>
            <div className="opacity-60 text-[8px]">SERIES 2026 © ALL SPECULATIONS AUTHORIZED UNDER DISTRIBUTED CREDENTIALS</div>
          </footer>

        </div>
      } />
    </Routes>
  );
}
