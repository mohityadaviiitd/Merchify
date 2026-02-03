import { useEffect, useState } from 'react'
import api from '../lib/api_with_auth'

export default function Checkout(){
  const [processing, setProcessing] = useState(false)
  const [message, setMessage] = useState('')

  const start = async ()=>{
    setProcessing(true)
    try{
      // Create order from cart
      const create = await api.post('/orders/')
      const order = create.data
      // Create a Stripe Checkout Session and redirect the browser
      const sessionRes = await api.post(`/orders/${order.id}/create_checkout_session/`)
      const { url } = sessionRes.data
      if (url) {
        window.location.href = url
        return
      }
      setMessage('Failed to get checkout URL')
    }catch(err:any){
      setMessage('Checkout failed: ' + (err?.response?.data?.error || err.message))
    }finally{ setProcessing(false) }
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-4">Checkout</h2>
      <div className="mb-4">Note: This demo uses a test token. Replace with real Stripe integration for production.</div>
      <button disabled={processing} onClick={start} className="px-4 py-2 bg-green-600 text-white rounded">{processing? 'Processing...' : 'Pay & Place Order'}</button>
      {message && <div className="mt-4">{message}</div>}
    </div>
  )
}
