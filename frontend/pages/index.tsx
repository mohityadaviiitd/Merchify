import Link from 'next/link'

export default function Home() {
  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-4">Merchify</h1>
      <p className="mb-6">Simple MERCH CRUD application. Purpose: As an assignment of Social Booster Media.</p>
      <div className="space-x-4">
        <Link href="/products" className="px-4 py-2 bg-blue-600 text-white rounded">Browse Products</Link>
        <Link href="/admin-dashboard" className="px-4 py-2 bg-gray-200 rounded">Admin</Link>
      </div>
    </div>
  )
}
