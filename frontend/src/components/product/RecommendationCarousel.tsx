import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Star, ChevronLeft, ChevronRight, Sparkles } from 'lucide-react';
import { apiClient } from '@frontend/src/lib/api-client';
import { useAuth } from '@frontend/src/contexts/AuthContext';
import ImageWithFallback from '@frontend/src/components/product/ImageWithFallback';

interface RecommendedProduct {
    id: string;
    name: string;
    price: string;
    rating_avg: string;
    primary_image_url: string | null;
    reason: string;
}

export default function RecommendationCarousel() {
    const navigate = useNavigate();
    const { user } = useAuth();
    const scrollRef = useRef<HTMLDivElement>(null);
    const [products, setProducts] = useState<RecommendedProduct[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        if (!user) {
            setLoading(false);
            return;
        }

        const fetchRecommendations = async () => {
            try {
                const data = await apiClient.get<{ results: RecommendedProduct[] }>(
                    '/ai/recommendations',
                    { user_id: user.id }
                );
                const results = Array.isArray(data) ? data : (data as any).results || [];
                setProducts(results.slice(0, 10));
            } catch {
                setError(true);
            } finally {
                setLoading(false);
            }
        };

        fetchRecommendations();
    }, [user]);

    const scroll = (direction: 'left' | 'right') => {
        if (!scrollRef.current) return;
        const scrollAmount = 280;
        scrollRef.current.scrollBy({
            left: direction === 'left' ? -scrollAmount : scrollAmount,
            behavior: 'smooth',
        });
    };

    // Hide section on error or if user is not logged in
    if (error || !user) return null;

    // Loading skeleton
    if (loading) {
        return (
            <section className="space-y-4">
                <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-blue-600" />
                    <h2 className="text-xl md:text-2xl font-bold text-gray-900">Recommended for You</h2>
                </div>
                <div className="flex gap-4 overflow-hidden">
                    {Array.from({ length: 5 }).map((_, i) => (
                        <div
                            key={i}
                            className="flex-shrink-0 w-[240px] rounded-xl bg-white border border-gray-100 overflow-hidden animate-pulse"
                        >
                            <div className="w-full h-[160px] bg-gray-200" />
                            <div className="p-3 space-y-2">
                                <div className="h-4 w-3/4 bg-gray-200 rounded" />
                                <div className="h-3 w-1/2 bg-gray-100 rounded" />
                                <div className="h-3 w-2/3 bg-gray-100 rounded" />
                            </div>
                        </div>
                    ))}
                </div>
            </section>
        );
    }

    // Don't render if no recommendations
    if (products.length === 0) return null;

    return (
        <section className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-blue-600" />
                    <h2 className="text-xl md:text-2xl font-bold text-gray-900">Recommended for You</h2>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => scroll('left')}
                        className="p-1.5 rounded-full border border-gray-200 hover:bg-gray-100 transition-colors"
                        aria-label="Scroll left"
                    >
                        <ChevronLeft className="w-4 h-4 text-gray-600" />
                    </button>
                    <button
                        onClick={() => scroll('right')}
                        className="p-1.5 rounded-full border border-gray-200 hover:bg-gray-100 transition-colors"
                        aria-label="Scroll right"
                    >
                        <ChevronRight className="w-4 h-4 text-gray-600" />
                    </button>
                </div>
            </div>

            <div
                ref={scrollRef}
                className="flex gap-4 overflow-x-auto scrollbar-hide pb-2"
                style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
            >
                {products.map((product) => (
                    <div
                        key={product.id}
                        onClick={() => navigate(`/products/${product.id}`)}
                        className="flex-shrink-0 w-[240px] rounded-xl bg-white border border-gray-100 hover:border-blue-200 hover:shadow-md transition-all overflow-hidden cursor-pointer group"
                    >
                        <div className="relative w-full h-[160px] bg-gray-50 overflow-hidden">
                            <ImageWithFallback
                                src={product.primary_image_url || ''}
                                alt={product.name}
                                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            />
                        </div>
                        <div className="p-3 space-y-1.5">
                            <h3 className="text-sm font-semibold text-gray-900 line-clamp-1 group-hover:text-blue-700 transition-colors">
                                {product.name}
                            </h3>
                            <div className="flex items-center justify-between">
                                <span className="text-base font-bold text-gray-900">
                                    ${parseFloat(product.price).toLocaleString()}
                                </span>
                                <div className="flex items-center gap-1">
                                    <Star className="w-3.5 h-3.5 text-yellow-400 fill-yellow-400" />
                                    <span className="text-xs font-medium text-gray-600">
                                        {parseFloat(product.rating_avg).toFixed(1)}
                                    </span>
                                </div>
                            </div>
                            {product.reason && (
                                <span className="inline-block text-[10px] font-medium text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full">
                                    {product.reason}
                                </span>
                            )}
                        </div>
                    </div>
                ))}
            </div>
        </section>
    );
}
