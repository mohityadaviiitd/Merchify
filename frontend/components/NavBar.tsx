import Link from 'next/link'
import React, { useEffect, useState } from 'react'
import api from '../lib/api_with_auth'
import { clearToken, getToken } from '../lib/auth'

export default function NavBar() {
  const [user, setUser] = useState<any | null>(undefined)

  useEffect(()=>{
    // Only fetch user if a token exists
    const token = getToken()
    if(!token){
      setUser(null)
      return
    }
    let mounted = true
    api.get('/auth/current-user/').then(res=>{
      if(mounted) setUser(res.data)
    }).catch(()=>{
      if(mounted) setUser(null)
    })
    return ()=> { mounted = false }
  },[])

  const handleLogout = ()=>{
    clearToken()
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <nav className="bg-white shadow">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex justify-between h-16 items-center">
          <div className="flex items-center space-x-6">
            <Link href="/" className="font-bold text-xl">
              Merchify
            </Link>
            <Link href="/products" className="text-gray-700 hover:text-gray-900">
              Products
            </Link>
          </div>
          <div className="flex items-center space-x-4">
            <Link href="/cart" className="text-gray-700 hover:text-gray-900">
              Cart
            </Link>

            {user === undefined ? (
              <>
                <Link href="/login" className="text-gray-700 hover:text-gray-900">Login</Link>
                <Link href="/register" className="text-gray-700 hover:text-gray-900">Register</Link>
              </>
            ) : user ? (
              <>
                <span className="text-gray-700">Hi, {user.username}</span>
                <button onClick={handleLogout} className="px-3 py-1 bg-red-600 text-white rounded">Logout</button>
              </>
            ) : (
              <>
                <Link href="/login" className="text-gray-700 hover:text-gray-900">Login</Link>
                <Link href="/register" className="text-gray-700 hover:text-gray-900">Register</Link>
              </>
            )}

            <Link href="/admin-dashboard" className="text-gray-700 hover:text-gray-900">
              Dashboard
            </Link>
          </div>
        </div>
      </div>
    </nav>
  )
}
