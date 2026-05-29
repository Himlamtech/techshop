import React from 'react';
import { Navigate } from 'react-router-dom';
import {
    Package,
    ShoppingCart,
    DollarSign,
    Users,
    Brain,
    Activity,
    BarChart3,
} from 'lucide-react';
import { useAuth } from '@frontend/src/contexts/AuthContext';

// Placeholder data for overview metrics
const OVERVIEW_METRICS = [
    { label: 'Total Products', value: '1,248', icon: Package, color: 'bg-blue-50 text-blue-600' },
    { label: 'Total Orders', value: '3,672', icon: ShoppingCart, color: 'bg-green-50 text-green-600' },
    { label: 'Revenue', value: '$284,500', icon: DollarSign, color: 'bg-purple-50 text-purple-600' },
    { label: 'Active Users', value: '892', icon: Users, color: 'bg-orange-50 text-orange-600' },
];

// Placeholder product data
const PRODUCTS_DATA = [
    { id: '1', name: 'MacBook Pro 16"', category: 'Laptops', price: '$2,499', stock: 45, status: 'active' },
    { id: '2', name: 'Sony WH-1000XM5', category: 'Audio', price: '$349', stock: 120, status: 'active' },
    { id: '3', name: 'iPhone 15 Pro Max', category: 'Smartphones', price: '$1,199', stock: 0, status: 'out_of_stock' },
    { id: '4', name: 'Samsung 4K Monitor', category: 'Monitors', price: '$599', stock: 8, status: 'low_stock' },
    { id: '5', name: 'Logitech MX Master 3S', category: 'Peripherals', price: '$99', stock: 200, status: 'active' },
];

// Placeholder order data
const ORDERS_DATA = [
    { id: 'ORD-001', status: 'delivered', total: '$2,847', date: '2025-01-15' },
    { id: 'ORD-002', status: 'processing', total: '$449', date: '2025-01-14' },
    { id: 'ORD-003', status: 'shipped', total: '$1,298', date: '2025-01-13' },
    { id: 'ORD-004', status: 'pending', total: '$99', date: '2025-01-12' },
    { id: 'ORD-005', status: 'delivered', total: '$3,199', date: '2025-01-11' },
];

// AI model status data
const AI_MODELS = [
    { name: 'Sentiment Analysis', version: 'v2.3.1', lastRun: '2 hours ago', accuracy: '94.2%', icon: Brain },
    { name: 'Customer Segmentation', version: 'v1.8.0', lastRun: '6 hours ago', accuracy: '91.7%', icon: Users },
    { name: 'Product Classification', version: 'v3.1.0', lastRun: '1 hour ago', accuracy: '96.5%', icon: BarChart3 },
];

function getStatusBadge(status: string) {
    const styles: Record<string, string> = {
        active: 'bg-green-100 text-green-700',
        out_of_stock: 'bg-red-100 text-red-700',
        low_stock: 'bg-yellow-100 text-yellow-700',
        delivered: 'bg-green-100 text-green-700',
        processing: 'bg-blue-100 text-blue-700',
        shipped: 'bg-purple-100 text-purple-700',
        pending: 'bg-yellow-100 text-yellow-700',
    };
    return styles[status] || 'bg-gray-100 text-gray-700';
}

function formatStatus(status: string) {
    return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function AdminDashboardPage() {
    const { user } = useAuth();

    // Restrict access to admin role
    if (!user || user.role !== 'admin') {
        return <Navigate to="/" replace />;
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto px-4 md:px-8 py-8">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-2xl md:text-3xl font-bold text-gray-900">Admin Dashboard</h1>
                    <p className="text-sm text-gray-500 mt-1">Overview of your store performance and management tools</p>
                </div>

                {/* Overview Metrics */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                    {OVERVIEW_METRICS.map(({ label, value, icon: Icon, color }) => (
                        <div key={label} className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-500 font-medium">{label}</p>
                                    <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
                                </div>
                                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
                                    <Icon className="w-5 h-5" />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Product Management Table */}
                <div className="bg-white rounded-xl border border-gray-100 shadow-sm mb-8 overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-100">
                        <h2 className="text-lg font-semibold text-gray-900">Product Management</h2>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-6 py-3">Name</th>
                                    <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-6 py-3">Category</th>
                                    <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-6 py-3">Price</th>
                                    <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-6 py-3">Stock</th>
                                    <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-6 py-3">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-50">
                                {PRODUCTS_DATA.map((product) => (
                                    <tr key={product.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-6 py-4 text-sm font-medium text-gray-900">{product.name}</td>
                                        <td className="px-6 py-4 text-sm text-gray-600">{product.category}</td>
                                        <td className="px-6 py-4 text-sm font-medium text-gray-900">{product.price}</td>
                                        <td className="px-6 py-4 text-sm text-gray-600">{product.stock}</td>
                                        <td className="px-6 py-4">
                                            <span className={`inline-flex text-xs font-medium px-2.5 py-0.5 rounded-full ${getStatusBadge(product.status)}`}>
                                                {formatStatus(product.status)}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Order Management Table */}
                <div className="bg-white rounded-xl border border-gray-100 shadow-sm mb-8 overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-100">
                        <h2 className="text-lg font-semibold text-gray-900">Order Management</h2>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-6 py-3">Order ID</th>
                                    <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-6 py-3">Status</th>
                                    <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-6 py-3">Total</th>
                                    <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-6 py-3">Date</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-50">
                                {ORDERS_DATA.map((order) => (
                                    <tr key={order.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-6 py-4 text-sm font-medium text-gray-900">{order.id}</td>
                                        <td className="px-6 py-4">
                                            <span className={`inline-flex text-xs font-medium px-2.5 py-0.5 rounded-full ${getStatusBadge(order.status)}`}>
                                                {formatStatus(order.status)}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-sm font-medium text-gray-900">{order.total}</td>
                                        <td className="px-6 py-4 text-sm text-gray-600">{order.date}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* AI Model Status Cards */}
                <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-100">
                        <h2 className="text-lg font-semibold text-gray-900">AI Model Status</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-6">
                        {AI_MODELS.map(({ name, version, lastRun, accuracy, icon: Icon }) => (
                            <div key={name} className="border border-gray-100 rounded-lg p-4 space-y-3">
                                <div className="flex items-center gap-3">
                                    <div className="w-9 h-9 rounded-lg bg-indigo-50 flex items-center justify-center">
                                        <Icon className="w-4.5 h-4.5 text-indigo-600" />
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-semibold text-gray-900">{name}</h3>
                                        <p className="text-xs text-gray-500">{version}</p>
                                    </div>
                                </div>
                                <div className="flex items-center justify-between text-xs">
                                    <div className="flex items-center gap-1.5">
                                        <Activity className="w-3.5 h-3.5 text-green-500" />
                                        <span className="text-gray-600">Last run: {lastRun}</span>
                                    </div>
                                    <span className="font-semibold text-gray-900">{accuracy}</span>
                                </div>
                                <div className="w-full bg-gray-100 rounded-full h-1.5">
                                    <div
                                        className="bg-indigo-500 h-1.5 rounded-full"
                                        style={{ width: accuracy }}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
