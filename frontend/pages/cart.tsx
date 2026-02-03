import { useEffect, useState } from 'react'
import Link from 'next/link'
import api from '../lib/api_with_auth'
import { clearToken } from '../lib/auth'

type Item = { id:number, product_name:string, product_price:string | number, quantity:number }

export default function Cart(){
  const [cart, setCart] = useState<any>(null)
  const [error, setError] = useState('')

  useEffect(()=>{
    api.get('/cart/my_cart/').then(res=> setCart(res.data)).catch(err=> setError('Please login to view cart'))
  },[])

  if(error) return <div className="p-6">{error}</div>

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-4">My Cart</h2>
      {!cart ? <div>Loading...</div> : (
        <div>
          {cart.items.length===0 && <div>Your cart is empty</div>}
          <div className="space-y-3">
            {cart.items.map((it:Item)=> {
              const name = it.product_name || 'Product'
              const price = parseFloat(it.product_price as string) || 0
              const lineTotal = (price * (it.quantity || 0))
              return (
                <div key={it.id} className="p-3 border rounded flex justify-between">
                  <div>
                    <div className="font-semibold">{name}</div>
                    <div className="text-sm text-gray-600">Qty: {it.quantity}</div>
                  </div>
                  <div className="text-right">${lineTotal.toFixed(2)}</div>
                </div>
              )
            })}
          </div>
          <div className="mt-4 font-bold">Total: ${parseFloat(cart.total_price || 0).toFixed(2)}</div>
          <div className="mt-3">
            <Link href="/checkout" className="px-4 py-2 bg-blue-600 text-white rounded">Proceed to Checkout</Link>
          </div>
        </div>
      )}
    </div>
  )
}
