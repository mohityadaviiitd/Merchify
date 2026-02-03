import { useEffect } from 'react'
import { useRouter } from 'next/router'

export default function CheckoutSuccess(){
  const router = useRouter()

  useEffect(()=>{
    // redirect to products after a short delay
    const t = setTimeout(()=> router.push('/products'), 1500)
    return ()=> clearTimeout(t)
  },[router])

  return (
    <div className="max-w-2xl mx-auto p-6 text-center">
      <h2 className="text-2xl font-bold mb-4">Thank you — order placed</h2>
      <p className="text-gray-600">You will be redirected to products shortly.</p>
    </div>
  )
}
