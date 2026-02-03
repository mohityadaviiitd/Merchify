import { useState } from 'react'
import api from '../lib/api'
import { useRouter } from 'next/router'

export default function Register(){
  const [form, setForm] = useState({username:'', email:'', password:'', role:'user'})
  const [error, setError] = useState('')
  const router = useRouter()

  const submit = async (e:any) =>{
    e.preventDefault()
    try{
      await api.post('/auth/register/', form)
      router.push('/login')
    }catch(err:any){
      setError(JSON.stringify(err?.response?.data || 'Registration failed'))
    }
  }

  return (
    <div className="max-w-md mx-auto p-6">
      <h2 className="text-2xl font-bold mb-4">Register</h2>
      <form onSubmit={submit} className="space-y-3">
        <input className="w-full border p-2" placeholder="Username" value={form.username} onChange={e=>setForm({...form, username:e.target.value})} />
        <input className="w-full border p-2" placeholder="Email" value={form.email} onChange={e=>setForm({...form, email:e.target.value})} />
        <input className="w-full border p-2" placeholder="Password" type="password" value={form.password} onChange={e=>setForm({...form, password:e.target.value})} />
        <div className="flex items-center space-x-4">
          <label className="flex items-center">
            <input type="radio" name="role" value="user" checked={form.role==='user'} onChange={()=>setForm({...form, role:'user'})} className="mr-1" /> User
          </label>
          <label className="flex items-center">
            <input type="radio" name="role" value="admin" checked={form.role==='admin'} onChange={()=>setForm({...form, role:'admin'})} className="mr-1" /> Admin
          </label>
        </div>
        {error && <div className="text-red-600">{error}</div>}
        <button className="bg-green-600 text-white px-4 py-2 rounded">Register</button>
      </form>
    </div>
  )
}
