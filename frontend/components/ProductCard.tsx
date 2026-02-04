import React, { useState } from 'react'
import api from '../lib/api_with_auth'

type Props = {
  id: number
  name: string
  description: string
  price: number
  image?: string
}

export default function ProductCard({ id, name, description, price, image }: Props) {
  const [loading, setLoading] = useState(false)

  const addToCart = async () => {
    setLoading(true)
    try {
      await api.post('/cart/add_item/', { product_id: id, quantity: 1 })
      if (typeof window !== 'undefined') alert('Added to cart')
    } catch (err: any) {
      const msg = err?.response?.data || err.message || 'Failed to add to cart'
      if (typeof window !== 'undefined') alert('Error: ' + JSON.stringify(msg))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="border rounded p-4 shadow-sm">
      {image && <img src={image} alt={name} className="w-full h-40 object-contain mb-2" />}
      <h3 className="font-semibold text-lg">{name}</h3>
      <p className="text-sm text-gray-600">{description}</p>
      <div className="mt-2 font-bold">₹{price.toFixed(2)}</div>
      <button onClick={addToCart} disabled={loading} className="mt-3 bg-blue-600 text-white px-3 py-1 rounded">
        {loading ? 'Adding...' : 'Add to cart'}
      </button>
    </div>
  )
}
