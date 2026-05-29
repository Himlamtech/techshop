import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Star,
    ShoppingCart,
    Plus,
    Minus,
    MessageSquare,
    ChevronLeft,
    Package,
    AlertCircle,
} from 'lucide-react';
import { apiClient } from '@frontend/src/lib/api-client';
import ImageWithFallback from '@frontend/src/components/product/ImageWithFallback';
import ErrorState from '@frontend/src/components/product/ErrorState';

// --- Types ---

interface ProductImage {
    id: string;
    image_url: string;
    is_primary: boolean;
    sort_order: number;
}

interface ProductDetail {
    id: string;
    sku: string;
    name: string;
    slug: string;
    description: string;
    price: string;
    stock: number;
    brand: string;
    category_id: string;
    category_name: string;
    status: string;
    attributes: Record<string, string> | null;
    rating_avg: string;
    rating_count: number;
    images: ProductImage[];
    primary_image_url: string | null;
}

// --- Skeleton Loading Component ---

function ProductDetailSkeleton() {
    return (
        <div className="animate-pulse">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Image gallery skeleton */}
                <div className="space-y-4">
                    <div className="w-full aspect-square bg-gray-200 rounded-2xl" />
                    <div className="flex gap-2">
                        {Array.from({ length: 4 }).map((_, i) => (
                            <div key={i} className="w-16 h-16 bg-gray-200 rounded-lg" />
                        ))}
                    </div>
                </div>

                {/* Info skeleton */}
                <div className="space-y-4">
                    <div className="h-4 w-24 bg-gray-200 rounded" />
                    <div className="h-8 w-3/4 bg-gray-200 rounded" />
                    <div className="h-4 w-32 bg-gray-200 rounded" />
                    <div className="h-10 w-40 bg-gray-200 rounded" />
                    <div className="h-4 w-28 bg-gray-200 rounded" />
                    <div className="flex gap-2">
                        <div className="h-7 w-20 bg-gray-100 rounded-full" />
                        <div className="h-7 w-24 bg-gray-100 rounded-full" />
                        <div className="h-7 w-16 bg-gray-100 rounded-full" />
                    </div>
                    <div className="h-12 w-full bg-gray-200 rounded-lg" />
                    <div className="h-12 w-full bg-gray-100 rounded-lg" />
                </div>
            </div>

            {/* Description skeleton */}
            <div className="mt-10 space-y-3">
                <div className="h-6 w-40 bg-gray-200 rounded" />
                <div className="h-4 w-full bg-gray-100 rounded" />
                <div className="h-4 w-5/6 bg-gray-100 rounded" />
                <div className="h-4 w-2/3 bg-gray-100 rounded" />
            </div>
        </div>
    );
}

// --- Not Found Component ---

function ProductNotFound() {
    const navigate = useNavigate();
    return (
        <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
            <div className="w-20 h-20 rounded-full bg-gray-100 flex items-center justify-center mb-6">
                <Package className="w-10 h-10 text-gray-400" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Product Not Found</h2>
            <p className="text-sm text-gray-500 max-w-sm mb-6">
                The product you're looking for doesn't exist or has been removed.
            </p>
            <button
                onClick={() => navigate('/products')}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
            >
                <ChevronLeft className="w-4 h-4" />
                Back to Products
            </button>
        </div>
    );
}

// --- Star Rating Component ---

function StarRating({ rating, count }: { rating: number; count: number }) {
    const fullStars = Math.floor(rating);
    const hasHalf = rating - fullStars >= 0.5;

    return (
        <div className="flex items-center gap-2">
            <div className="flex items-center gap-0.5">
                {Array.from({ length: 5 }).map((_, i) => (
                    <Star
                        key={i}
                        className={`w-4 h-4 ${i < fullStars
                                ? 'text-yellow-400 fill-yellow-400'
                                : i === fullStars && hasHalf
                                    ? 'text-yellow-400 fill-yellow-400/50'
                                    : 'text-gray-300'
                            }`}
                    />
                ))}
            </div>
            <span className="text-sm font-medium text-gray-700">{rating.toFixed(1)}</span>
            <span className="text-sm text-gray-500">({count} {count === 1 ? 'review' : 'reviews'})</span>
        </div>
    );
}

// --- Stock Badge Component ---

function StockBadge({ stock }: { stock: number }) {
    if (stock === 0) {
        return (
            <span className="inline-flex items-center gap-1 px-3 py-1 bg-red-50 text-red-700 text-xs font-semibold rounded-full">
                <AlertCircle className="w-3 h-3" />
                Out of Stock
            </span>
        );
    }
    if (stock <= 5) {
        return (
            <span className="inline-flex items-center gap-1 px-3 py-1 bg-orange-50 text-orange-700 text-xs font-semibold rounded-full">
                Only {stock} left
            </span>
        );
    }
    return (
        <span className="inline-flex items-center gap-1 px-3 py-1 bg-green-50 text-green-700 text-xs font-semibold rounded-full">
            In Stock
        </span>
    );
}

// --- Main Page Component ---

export default function ProductDetailPage() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();

    const [product, setProduct] = useState<ProductDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [notFound, setNotFound] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [selectedImageIndex, setSelectedImageIndex] = useState(0);
    const [quantity, setQuantity] = useState(1);
    const [addingToCart, setAddingToCart] = useState(false);
    const [cartSuccess, setCartSuccess] = useState(false);

    const fetchProduct = useCallback(async () => {
        if (!id) return;
        setLoading(true);
        setError(null);
        setNotFound(false);
        try {
            const data = await apiClient.get<ProductDetail>(`/catalog/products/${id}`);
            setProduct(data);
        } catch (err: any) {
            if (err?.status === 404) {
                setNotFound(true);
            } else {
                setError(err?.message || 'Failed to load product details');
            }
        } finally {
            setLoading(false);
        }
    }, [id]);

    useEffect(() => {
        fetchProduct();
    }, [fetchProduct]);

    // Reset quantity when product changes
    useEffect(() => {
        setQuantity(1);
        setSelectedImageIndex(0);
        setCartSuccess(false);
    }, [id]);

    const handleQuantityChange = (delta: number) => {
        setQuantity((prev) => {
            const next = prev + delta;
            const maxQty = Math.min(99, product?.stock || 99);
            if (next < 1) return 1;
            if (next > maxQty) return maxQty;
            return next;
        });
    };

    const handleAddToCart = async () => {
        if (!product || product.stock === 0) return;
        setAddingToCart(true);
        setCartSuccess(false);
        try {
            await apiClient.post('/cart/items', {
                product_id: product.id,
                quantity,
            });
            setCartSuccess(true);
            setTimeout(() => setCartSuccess(false), 3000);
        } catch (err: any) {
            alert(err?.message || 'Failed to add to cart');
        } finally {
            setAddingToCart(false);
        }
    };

    const handleAskAI = () => {
        navigate(`/?chat=true&product=${id}`);
    };

    // Build sorted images list
    const images: ProductImage[] = product?.images
        ? [...product.images].sort((a, b) => a.sort_order - b.sort_order)
        : [];

    const mainImageUrl =
        images.length > 0
            ? images[selectedImageIndex]?.image_url
            : product?.primary_image_url || '';

    // --- Render ---

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50">
                <div className="max-w-6xl mx-auto px-4 md:px-8 py-8">
                    <ProductDetailSkeleton />
                </div>
            </div>
        );
    }

    if (notFound) {
        return (
            <div className="min-h-screen bg-gray-50">
                <div className="max-w-6xl mx-auto px-4 md:px-8 py-8">
                    <ProductNotFound />
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gray-50">
                <div className="max-w-6xl mx-auto px-4 md:px-8 py-8">
                    <ErrorState title="Failed to load product" message={error} onRetry={fetchProduct} />
                </div>
            </div>
        );
    }

    if (!product) return null;

    const ratingAvg = parseFloat(product.rating_avg) || 0;
    const price = parseFloat(product.price);
    const attributes = product.attributes || {};
    const attributeEntries = Object.entries(attributes);

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-6xl mx-auto px-4 md:px-8 py-6 md:py-10">
                {/* Back navigation */}
                <button
                    onClick={() => navigate('/products')}
                    className="inline-flex items-center gap-1.5 text-sm text-gray-600 hover:text-blue-600 mb-6 transition-colors"
                >
                    <ChevronLeft className="w-4 h-4" />
                    Back to Products
                </button>

                {/* Main 2-column layout */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-12">
                    {/* Left: Image Gallery */}
                    <div className="space-y-4">
                        {/* Main image */}
                        <div className="w-full aspect-square bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-sm">
                            <ImageWithFallback
                                src={mainImageUrl}
                                alt={product.name}
                                className="w-full h-full object-contain p-4"
                            />
                        </div>

                        {/* Thumbnails */}
                        {images.length > 1 && (
                            <div className="flex gap-2 overflow-x-auto pb-1">
                                {images.map((img, idx) => (
                                    <button
                                        key={img.id}
                                        onClick={() => setSelectedImageIndex(idx)}
                                        className={`shrink-0 w-16 h-16 rounded-lg border-2 overflow-hidden transition-all ${idx === selectedImageIndex
                                                ? 'border-blue-500 ring-2 ring-blue-200'
                                                : 'border-gray-200 hover:border-gray-300'
                                            }`}
                                    >
                                        <ImageWithFallback
                                            src={img.image_url}
                                            alt={`${product.name} - ${idx + 1}`}
                                            className="w-full h-full object-cover"
                                        />
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Right: Product Info */}
                    <div className="space-y-5">
                        {/* Brand & Category */}
                        <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-semibold text-blue-600 uppercase tracking-wide">
                                {product.brand}
                            </span>
                            <span className="text-gray-300">•</span>
                            <span className="text-xs text-gray-500">{product.category_name}</span>
                        </div>

                        {/* Product Name */}
                        <h1 className="text-2xl md:text-3xl font-bold text-gray-900 leading-tight">
                            {product.name}
                        </h1>

                        {/* Rating */}
                        <StarRating rating={ratingAvg} count={product.rating_count} />

                        {/* Price */}
                        <div className="text-3xl font-bold text-gray-900">
                            ${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>

                        {/* Stock Status */}
                        <StockBadge stock={product.stock} />

                        {/* Key Specs as Chips */}
                        {attributeEntries.length > 0 && (
                            <div className="flex flex-wrap gap-2">
                                {attributeEntries.slice(0, 6).map(([key, value]) => (
                                    <span
                                        key={key}
                                        className="inline-flex items-center px-3 py-1.5 bg-gray-100 text-gray-700 text-xs font-medium rounded-full"
                                    >
                                        <span className="text-gray-500 mr-1">{key}:</span>
                                        {value}
                                    </span>
                                ))}
                            </div>
                        )}

                        {/* Quantity Selector + Add to Cart */}
                        <div className="pt-4 border-t border-gray-100 space-y-4">
                            {/* Quantity */}
                            <div className="flex items-center gap-3">
                                <span className="text-sm font-medium text-gray-700">Quantity:</span>
                                <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden">
                                    <button
                                        onClick={() => handleQuantityChange(-1)}
                                        disabled={quantity <= 1}
                                        className="p-2 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                                        aria-label="Decrease quantity"
                                    >
                                        <Minus className="w-4 h-4 text-gray-600" />
                                    </button>
                                    <span className="w-12 text-center text-sm font-semibold text-gray-900">
                                        {quantity}
                                    </span>
                                    <button
                                        onClick={() => handleQuantityChange(1)}
                                        disabled={quantity >= Math.min(99, product.stock)}
                                        className="p-2 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                                        aria-label="Increase quantity"
                                    >
                                        <Plus className="w-4 h-4 text-gray-600" />
                                    </button>
                                </div>
                                {product.stock > 0 && product.stock <= 20 && (
                                    <span className="text-xs text-gray-500">
                                        ({product.stock} available)
                                    </span>
                                )}
                            </div>

                            {/* Add to Cart Button */}
                            <button
                                onClick={handleAddToCart}
                                disabled={product.stock === 0 || addingToCart}
                                className={`w-full flex items-center justify-center gap-2 py-3 px-6 rounded-lg text-sm font-semibold transition-all ${cartSuccess
                                        ? 'bg-green-600 text-white'
                                        : product.stock === 0
                                            ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                                            : 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:shadow-md'
                                    }`}
                            >
                                <ShoppingCart className="w-4 h-4" />
                                {addingToCart
                                    ? 'Adding...'
                                    : cartSuccess
                                        ? 'Added to Cart!'
                                        : product.stock === 0
                                            ? 'Out of Stock'
                                            : 'Add to Cart'}
                            </button>

                            {/* Ask AI Button */}
                            <button
                                onClick={handleAskAI}
                                className="w-full flex items-center justify-center gap-2 py-3 px-6 rounded-lg text-sm font-semibold border border-blue-200 text-blue-700 bg-blue-50 hover:bg-blue-100 transition-colors"
                            >
                                <MessageSquare className="w-4 h-4" />
                                Ask AI about this product
                            </button>
                        </div>
                    </div>
                </div>

                {/* Below: Description, Specifications, Similar Products */}
                <div className="mt-10 space-y-8">
                    {/* Description */}
                    {product.description && (
                        <section className="bg-white rounded-2xl border border-gray-100 p-6 md:p-8 shadow-sm">
                            <h2 className="text-lg font-bold text-gray-900 mb-4">Description</h2>
                            <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                                {product.description}
                            </p>
                        </section>
                    )}

                    {/* Specifications Table */}
                    {attributeEntries.length > 0 && (
                        <section className="bg-white rounded-2xl border border-gray-100 p-6 md:p-8 shadow-sm">
                            <h2 className="text-lg font-bold text-gray-900 mb-4">Specifications</h2>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <tbody>
                                        {attributeEntries.map(([key, value], idx) => (
                                            <tr
                                                key={key}
                                                className={idx % 2 === 0 ? 'bg-gray-50' : 'bg-white'}
                                            >
                                                <td className="px-4 py-3 font-medium text-gray-700 w-1/3">
                                                    {key}
                                                </td>
                                                <td className="px-4 py-3 text-gray-600">
                                                    {value}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </section>
                    )}

                    {/* Similar Products Placeholder */}
                    <section className="bg-white rounded-2xl border border-gray-100 p-6 md:p-8 shadow-sm">
                        <h2 className="text-lg font-bold text-gray-900 mb-4">Similar Products</h2>
                        <p className="text-sm text-gray-500">
                            Similar product recommendations will appear here based on AI analysis.
                        </p>
                    </section>
                </div>
            </div>
        </div>
    );
}
