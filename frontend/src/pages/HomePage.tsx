import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Cpu,
    Headphones,
    Smartphone,
    Monitor,
    Gamepad2,
    Camera,
    Watch,
    HardDrive,
    ShieldCheck,
    Truck,
    CreditCard,
    Bot,
    Award,
    Star,
    ArrowRight,
} from 'lucide-react';
import { apiClient } from '@frontend/src/lib/api-client';
import ImageWithFallback from '@frontend/src/components/product/ImageWithFallback';
import ProductCardSkeleton from '@frontend/src/components/product/ProductCardSkeleton';
import ErrorState from '@frontend/src/components/product/ErrorState';
import RecommendationCarousel from '@frontend/src/components/product/RecommendationCarousel';

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

const CATEGORY_ICONS = [
    { icon: Cpu, label: 'Laptops', slug: 'laptops' },
    { icon: Smartphone, label: 'Smartphones', slug: 'smartphones' },
    { icon: Headphones, label: 'Audio', slug: 'audio' },
    { icon: Monitor, label: 'Monitors', slug: 'monitors' },
    { icon: Gamepad2, label: 'Gaming', slug: 'gaming' },
    { icon: Camera, label: 'Cameras', slug: 'cameras' },
    { icon: Watch, label: 'Wearables', slug: 'wearables' },
    { icon: HardDrive, label: 'Storage', slug: 'storage' },
];

const TRUST_INDICATORS = [
    { icon: ShieldCheck, label: 'Genuine Products', description: '100% authentic items' },
    { icon: Award, label: 'Warranty', description: 'Official manufacturer warranty' },
    { icon: Truck, label: 'Fast Shipping', description: 'Quick delivery nationwide' },
    { icon: CreditCard, label: 'Secure Payment', description: 'Encrypted transactions' },
    { icon: Bot, label: 'AI Advisor', description: 'Smart product recommendations' },
];

export default function HomePage() {
    const navigate = useNavigate();
    const [featuredProducts, setFeaturedProducts] = useState<CatalogProduct[]>([]);
    const [categories, setCategories] = useState<Category[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const [productsRes, categoriesRes] = await Promise.allSettled([
                apiClient.get<{ results: CatalogProduct[] }>('/catalog/products', {
                    page: '1',
                    page_size: '8',
                    sort: 'popular',
                }),
                apiClient.get<{ results: Category[] }>('/catalog/categories'),
            ]);

            if (productsRes.status === 'fulfilled') {
                const data = productsRes.value;
                setFeaturedProducts(Array.isArray(data) ? data : (data as any).results || []);
            }

            if (categoriesRes.status === 'fulfilled') {
                const data = categoriesRes.value;
                setCategories(Array.isArray(data) ? data : (data as any).results || []);
            }

            // If both failed, show error
            if (productsRes.status === 'rejected' && categoriesRes.status === 'rejected') {
                setError('Failed to load homepage data');
            }
        } catch (err) {
            setError('Failed to load homepage data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleCategoryClick = (slug: string) => {
        navigate(`/products?category=${slug}`);
    };

    return (
        <div className="space-y-12 md:space-y-16">
            {/* Hero Section */}
            <section className="relative overflow-hidden bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 rounded-2xl px-6 py-12 md:px-12 md:py-20 text-white">
                <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0djItSDI0di0yaDEyem0wLTMwVjBoLTJ2NEgyNFYwSDEydjRIMFY2aDEyVjRoMTJ2MmgxMlY0aDEyVjBoLTEyeiIvPjwvZz48L2c+PC9zdmc+')] opacity-30" />
                <div className="relative z-10 max-w-3xl">
                    <h1 className="text-3xl md:text-5xl font-bold tracking-tight mb-4">
                        Discover the Latest in Tech
                    </h1>
                    <p className="text-blue-100 text-base md:text-lg mb-8 max-w-xl">
                        Shop premium technology products with AI-powered recommendations, expert reviews, and fast delivery.
                    </p>
                    <button
                        onClick={() => navigate('/products')}
                        className="inline-flex items-center gap-2 bg-white text-blue-700 font-semibold px-6 py-3 rounded-lg hover:bg-blue-50 transition-colors"
                    >
                        Browse All Products
                        <ArrowRight className="w-4 h-4" />
                    </button>
                </div>
            </section>

            {/* Category Shortcuts */}
            <section>
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl md:text-2xl font-bold text-gray-900">Shop by Category</h2>
                    <button
                        onClick={() => navigate('/products')}
                        className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
                    >
                        View all <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                </div>
                <div className="grid grid-cols-4 md:grid-cols-8 gap-3 md:gap-4">
                    {CATEGORY_ICONS.map(({ icon: Icon, label, slug }) => (
                        <button
                            key={slug}
                            onClick={() => handleCategoryClick(slug)}
                            className="flex flex-col items-center gap-2 p-3 md:p-4 rounded-xl bg-white border border-gray-100 hover:border-blue-200 hover:shadow-md transition-all group"
                        >
                            <div className="w-10 h-10 md:w-12 md:h-12 rounded-full bg-blue-50 group-hover:bg-blue-100 flex items-center justify-center transition-colors">
                                <Icon className="w-5 h-5 md:w-6 md:h-6 text-blue-600" />
                            </div>
                            <span className="text-xs md:text-sm font-medium text-gray-700 text-center">{label}</span>
                        </button>
                    ))}
                </div>
            </section>

            {/* Featured Products */}
            <section>
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl md:text-2xl font-bold text-gray-900">Featured Products</h2>
                    <button
                        onClick={() => navigate('/products')}
                        className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
                    >
                        See all <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                </div>

                {error && !loading && featuredProducts.length === 0 ? (
                    <ErrorState message={error} onRetry={fetchData} />
                ) : loading ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
                        {Array.from({ length: 4 }).map((_, i) => (
                            <ProductCardSkeleton key={i} />
                        ))}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
                        {featuredProducts.slice(0, 8).map((product) => (
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
                                    <div className="mt-auto flex items-center justify-between">
                                        <span className="text-lg font-bold text-gray-900">
                                            ${parseFloat(product.price).toLocaleString()}
                                        </span>
                                        <div className="flex items-center gap-1">
                                            <Star className="w-3.5 h-3.5 text-yellow-400 fill-yellow-400" />
                                            <span className="text-xs font-medium text-gray-600">
                                                {parseFloat(product.rating_avg).toFixed(1)}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {/* AI Recommendations Carousel */}
            <RecommendationCarousel />

            {/* Trust Indicators */}
            <section className="bg-gray-50 rounded-2xl p-6 md:p-8">
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 md:gap-6">
                    {TRUST_INDICATORS.map(({ icon: Icon, label, description }) => (
                        <div key={label} className="flex flex-col items-center text-center gap-2">
                            <div className="w-12 h-12 rounded-full bg-white shadow-sm flex items-center justify-center">
                                <Icon className="w-5 h-5 text-blue-600" />
                            </div>
                            <span className="text-sm font-semibold text-gray-900">{label}</span>
                            <span className="text-xs text-gray-500">{description}</span>
                        </div>
                    ))}
                </div>
            </section>
        </div>
    );
}
