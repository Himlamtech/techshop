import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
    Search,
    SlidersHorizontal,
    Star,
    ChevronLeft,
    ChevronRight,
    X,
} from 'lucide-react';
import { apiClient } from '@frontend/src/lib/api-client';
import ImageWithFallback from '@frontend/src/components/product/ImageWithFallback';
import ProductCardSkeleton from '@frontend/src/components/product/ProductCardSkeleton';
import EmptyState from '@frontend/src/components/product/EmptyState';
import ErrorState from '@frontend/src/components/product/ErrorState';

interface CatalogProduct {
    id: string;
    name: string;
    slug: string;
    price: string;
    stock: number;
    brand: string;
    category_name: string;
    rating_avg: string;
    rating_count: number;
    primary_image_url: string | null;
    status: string;
}

interface Category {
    id: string;
    name: string;
    slug: string;
}

interface PaginatedResponse {
    results: CatalogProduct[];
    count: number;
    page: number;
    page_size: number;
    total_pages: number;
}

const SORT_OPTIONS = [
    { value: 'popular', label: 'Popular' },
    { value: 'newest', label: 'Newest' },
    { value: 'price_asc', label: 'Price: Low to High' },
    { value: 'price_desc', label: 'Price: High to Low' },
    { value: 'rating', label: 'Top Rated' },
];

const PAGE_SIZE = 12;

export default function ProductListingPage() {
    const [searchParams, setSearchParams] = useSearchParams();
    const navigate = useNavigate();

    // State
    const [products, setProducts] = useState<CatalogProduct[]>([]);
    const [categories, setCategories] = useState<Category[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [totalPages, setTotalPages] = useState(1);
    const [totalCount, setTotalCount] = useState(0);
    const [filtersOpen, setFiltersOpen] = useState(false);

    // Filter state from URL params
    const currentPage = parseInt(searchParams.get('page') || '1', 10);
    const currentSort = searchParams.get('sort') || 'newest';
    const currentCategory = searchParams.get('category') || '';
    const currentBrand = searchParams.get('brand') || '';
    const currentMinPrice = searchParams.get('min_price') || '';
    const currentMaxPrice = searchParams.get('max_price') || '';
    const currentSearch = searchParams.get('search') || '';
    const currentRating = searchParams.get('min_rating') || '';

    // Local filter inputs (for the form before applying)
    const [searchInput, setSearchInput] = useState(currentSearch);
    const [minPriceInput, setMinPriceInput] = useState(currentMinPrice);
    const [maxPriceInput, setMaxPriceInput] = useState(currentMaxPrice);
    const [brandInput, setBrandInput] = useState(currentBrand);
    const [ratingInput, setRatingInput] = useState(currentRating);

    // Sync local inputs when URL params change
    useEffect(() => {
        setSearchInput(currentSearch);
        setMinPriceInput(currentMinPrice);
        setMaxPriceInput(currentMaxPrice);
        setBrandInput(currentBrand);
        setRatingInput(currentRating);
    }, [currentSearch, currentMinPrice, currentMaxPrice, currentBrand, currentRating]);

    const fetchProducts = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const params: Record<string, string> = {
                page: String(currentPage),
                page_size: String(PAGE_SIZE),
                sort: currentSort,
            };
            if (currentSearch) params.search = currentSearch;
            if (currentCategory) params.category = currentCategory;
            if (currentBrand) params.brand = currentBrand;
            if (currentMinPrice) params.min_price = currentMinPrice;
            if (currentMaxPrice) params.max_price = currentMaxPrice;
            if (currentRating) params.min_rating = currentRating;

            const data = await apiClient.get<PaginatedResponse>('/catalog/products', params);

            if (data && typeof data === 'object' && 'results' in data) {
                setProducts(data.results);
                setTotalPages(data.total_pages || 1);
                setTotalCount(data.count || 0);
            } else if (Array.isArray(data)) {
                setProducts(data as unknown as CatalogProduct[]);
                setTotalPages(1);
                setTotalCount((data as unknown as CatalogProduct[]).length);
            } else {
                setProducts([]);
                setTotalPages(1);
                setTotalCount(0);
            }
        } catch (err: any) {
            setError(err?.message || 'Failed to load products');
            setProducts([]);
        } finally {
            setLoading(false);
        }
    }, [currentPage, currentSort, currentSearch, currentCategory, currentBrand, currentMinPrice, currentMaxPrice, currentRating]);

    const fetchCategories = useCallback(async () => {
        try {
            const data = await apiClient.get<{ results: Category[] } | Category[]>('/catalog/categories');
            if (Array.isArray(data)) {
                setCategories(data);
            } else if (data && 'results' in data) {
                setCategories(data.results);
            }
        } catch {
            // Categories are non-critical, silently fail
        }
    }, []);

    useEffect(() => {
        fetchProducts();
    }, [fetchProducts]);

    useEffect(() => {
        fetchCategories();
    }, [fetchCategories]);

    // URL param helpers
    const updateParams = (updates: Record<string, string>) => {
        const newParams = new URLSearchParams(searchParams);
        Object.entries(updates).forEach(([key, value]) => {
            if (value) {
                newParams.set(key, value);
            } else {
                newParams.delete(key);
            }
        });
        // Reset to page 1 when filters change (unless page is being set)
        if (!('page' in updates)) {
            newParams.set('page', '1');
        }
        setSearchParams(newParams);
    };

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        updateParams({ search: searchInput });
    };

    const handleApplyFilters = () => {
        updateParams({
            brand: brandInput,
            min_price: minPriceInput,
            max_price: maxPriceInput,
            min_rating: ratingInput,
        });
        setFiltersOpen(false);
    };

    const handleClearFilters = () => {
        setSearchInput('');
        setMinPriceInput('');
        setMaxPriceInput('');
        setBrandInput('');
        setRatingInput('');
        setSearchParams(new URLSearchParams());
    };

    const handlePageChange = (page: number) => {
        updateParams({ page: String(page) });
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const hasActiveFilters = currentCategory || currentBrand || currentMinPrice || currentMaxPrice || currentSearch || currentRating;

    return (
        <div className="flex flex-col lg:flex-row gap-6">
            {/* Mobile filter toggle */}
            <div className="lg:hidden flex items-center justify-between mb-2">
                <button
                    onClick={() => setFiltersOpen(!filtersOpen)}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                    <SlidersHorizontal className="w-4 h-4" />
                    Filters
                    {hasActiveFilters && (
                        <span className="w-2 h-2 rounded-full bg-blue-600" />
                    )}
                </button>
                <span className="text-sm text-gray-500">{totalCount} products</span>
            </div>

            {/* Sidebar Filters */}
            <aside
                className={`${filtersOpen ? 'block' : 'hidden'
                    } lg:block w-full lg:w-64 shrink-0`}
            >
                <div className="bg-white rounded-xl border border-gray-100 p-5 space-y-5 sticky top-4">
                    <div className="flex items-center justify-between">
                        <h3 className="font-semibold text-gray-900">Filters</h3>
                        {hasActiveFilters && (
                            <button
                                onClick={handleClearFilters}
                                className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                            >
                                Clear all
                            </button>
                        )}
                    </div>

                    {/* Category filter */}
                    <div>
                        <label className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2 block">
                            Category
                        </label>
                        <div className="space-y-1 max-h-40 overflow-y-auto">
                            <button
                                onClick={() => updateParams({ category: '' })}
                                className={`block w-full text-left text-sm px-2 py-1.5 rounded ${!currentCategory ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-600 hover:bg-gray-50'
                                    }`}
                            >
                                All Categories
                            </button>
                            {categories.map((cat) => (
                                <button
                                    key={cat.id}
                                    onClick={() => updateParams({ category: cat.slug })}
                                    className={`block w-full text-left text-sm px-2 py-1.5 rounded ${currentCategory === cat.slug
                                            ? 'bg-blue-50 text-blue-700 font-medium'
                                            : 'text-gray-600 hover:bg-gray-50'
                                        }`}
                                >
                                    {cat.name}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Brand filter */}
                    <div>
                        <label className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2 block">
                            Brand
                        </label>
                        <input
                            type="text"
                            value={brandInput}
                            onChange={(e) => setBrandInput(e.target.value)}
                            placeholder="e.g. Apple, Samsung"
                            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                    </div>

                    {/* Price range filter */}
                    <div>
                        <label className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2 block">
                            Price Range
                        </label>
                        <div className="flex items-center gap-2">
                            <input
                                type="number"
                                value={minPriceInput}
                                onChange={(e) => setMinPriceInput(e.target.value)}
                                placeholder="Min"
                                min="0"
                                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                            <span className="text-gray-400">–</span>
                            <input
                                type="number"
                                value={maxPriceInput}
                                onChange={(e) => setMaxPriceInput(e.target.value)}
                                placeholder="Max"
                                min="0"
                                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                        </div>
                    </div>

                    {/* Rating filter */}
                    <div>
                        <label className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2 block">
                            Minimum Rating
                        </label>
                        <div className="flex gap-1">
                            {[1, 2, 3, 4, 5].map((rating) => (
                                <button
                                    key={rating}
                                    onClick={() => setRatingInput(ratingInput === String(rating) ? '' : String(rating))}
                                    className={`flex items-center gap-0.5 px-2 py-1 rounded text-xs font-medium border transition-colors ${parseInt(ratingInput) === rating
                                            ? 'bg-yellow-50 border-yellow-300 text-yellow-700'
                                            : 'border-gray-200 text-gray-500 hover:border-gray-300'
                                        }`}
                                >
                                    <Star className="w-3 h-3 fill-current" />
                                    {rating}+
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Apply button */}
                    <button
                        onClick={handleApplyFilters}
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2.5 rounded-lg transition-colors"
                    >
                        Apply Filters
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex-1 min-w-0">
                {/* Top bar: search + sort */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mb-6">
                    <form onSubmit={handleSearch} className="flex-1 relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            value={searchInput}
                            onChange={(e) => setSearchInput(e.target.value)}
                            placeholder="Search products..."
                            className="w-full text-sm bg-white border border-gray-200 rounded-lg pl-10 pr-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                        {searchInput && (
                            <button
                                type="button"
                                onClick={() => {
                                    setSearchInput('');
                                    updateParams({ search: '' });
                                }}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        )}
                    </form>

                    <select
                        value={currentSort}
                        onChange={(e) => updateParams({ sort: e.target.value })}
                        className="text-sm bg-white border border-gray-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                        {SORT_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                                {opt.label}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Active filter chips */}
                {hasActiveFilters && (
                    <div className="flex flex-wrap gap-2 mb-4">
                        {currentSearch && (
                            <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded-full">
                                Search: {currentSearch}
                                <button onClick={() => updateParams({ search: '' })}><X className="w-3 h-3" /></button>
                            </span>
                        )}
                        {currentCategory && (
                            <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded-full">
                                Category: {currentCategory}
                                <button onClick={() => updateParams({ category: '' })}><X className="w-3 h-3" /></button>
                            </span>
                        )}
                        {currentBrand && (
                            <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded-full">
                                Brand: {currentBrand}
                                <button onClick={() => updateParams({ brand: '' })}><X className="w-3 h-3" /></button>
                            </span>
                        )}
                        {(currentMinPrice || currentMaxPrice) && (
                            <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded-full">
                                Price: ${currentMinPrice || '0'} – ${currentMaxPrice || '∞'}
                                <button onClick={() => updateParams({ min_price: '', max_price: '' })}><X className="w-3 h-3" /></button>
                            </span>
                        )}
                        {currentRating && (
                            <span className="inline-flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded-full">
                                Rating: {currentRating}+
                                <button onClick={() => updateParams({ min_rating: '' })}><X className="w-3 h-3" /></button>
                            </span>
                        )}
                    </div>
                )}

                {/* Product Grid */}
                {error ? (
                    <ErrorState message={error} onRetry={fetchProducts} />
                ) : loading ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
                        {Array.from({ length: PAGE_SIZE }).map((_, i) => (
                            <ProductCardSkeleton key={i} />
                        ))}
                    </div>
                ) : products.length === 0 ? (
                    <EmptyState onReset={handleClearFilters} />
                ) : (
                    <>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
                            {products.map((product) => (
                                <div
                                    key={product.id}
                                    onClick={() => navigate(`/products/${product.id}`)}
                                    className="group flex flex-col rounded-2xl bg-white border border-gray-100 hover:border-blue-200 hover:shadow-lg transition-all overflow-hidden cursor-pointer"
                                >
                                    <div className="relative pt-[75%] w-full bg-gray-50 overflow-hidden">
                                        <ImageWithFallback
                                            src={product.primary_image_url || ''}
                                            alt={product.name}
                                            className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                        />
                                        {product.stock <= 5 && product.stock > 0 && (
                                            <span className="absolute top-2 right-2 bg-orange-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                                                Low Stock
                                            </span>
                                        )}
                                        {product.stock === 0 && (
                                            <span className="absolute top-2 right-2 bg-red-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                                                Out of Stock
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex flex-col flex-grow p-4">
                                        <span className="text-[10px] font-semibold text-blue-600 uppercase tracking-wide mb-1">
                                            {product.category_name || product.brand}
                                        </span>
                                        <h3 className="text-sm font-semibold text-gray-900 line-clamp-2 mb-2 group-hover:text-blue-700 transition-colors">
                                            {product.name}
                                        </h3>
                                        <div className="mt-auto flex items-center justify-between pt-2">
                                            <span className="text-lg font-bold text-gray-900">
                                                ${parseFloat(product.price).toLocaleString()}
                                            </span>
                                            <div className="flex items-center gap-1">
                                                <Star className="w-3.5 h-3.5 text-yellow-400 fill-yellow-400" />
                                                <span className="text-xs font-medium text-gray-600">
                                                    {parseFloat(product.rating_avg).toFixed(1)}
                                                </span>
                                                <span className="text-xs text-gray-400">({product.rating_count})</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div className="flex items-center justify-center gap-2 mt-8">
                                <button
                                    onClick={() => handlePageChange(currentPage - 1)}
                                    disabled={currentPage <= 1}
                                    className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                                >
                                    <ChevronLeft className="w-4 h-4" />
                                </button>

                                {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                                    let pageNum: number;
                                    if (totalPages <= 7) {
                                        pageNum = i + 1;
                                    } else if (currentPage <= 4) {
                                        pageNum = i + 1;
                                    } else if (currentPage >= totalPages - 3) {
                                        pageNum = totalPages - 6 + i;
                                    } else {
                                        pageNum = currentPage - 3 + i;
                                    }
                                    return (
                                        <button
                                            key={pageNum}
                                            onClick={() => handlePageChange(pageNum)}
                                            className={`w-9 h-9 rounded-lg text-sm font-medium transition-colors ${pageNum === currentPage
                                                    ? 'bg-blue-600 text-white'
                                                    : 'border border-gray-200 text-gray-600 hover:bg-gray-50'
                                                }`}
                                        >
                                            {pageNum}
                                        </button>
                                    );
                                })}

                                <button
                                    onClick={() => handlePageChange(currentPage + 1)}
                                    disabled={currentPage >= totalPages}
                                    className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
                                >
                                    <ChevronRight className="w-4 h-4" />
                                </button>
                            </div>
                        )}

                        {/* Results count */}
                        <p className="text-center text-xs text-gray-500 mt-4">
                            Showing {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, totalCount)} of {totalCount} products
                        </p>
                    </>
                )}
            </div>
        </div>
    );
}
