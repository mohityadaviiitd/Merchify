import { useEffect, useState } from 'react'
import api from '../lib/api'
import apiAuth from '../lib/api_with_auth'
import ProductCard from '../components/ProductCard'

type Product = {
  id: number
  name: string
  description: string
  price: number
  stock?: number
  image?: string | null
}

export default function ProductsPage(){
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState<any>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState({name:'', description:'', price:'', stock:'', image: null as File | null})
  const [editId, setEditId] = useState<number|null>(null)
  const [editForm, setEditForm] = useState({name:'', description:'', price:'', stock:''})

  // Fetch products
  const fetchProducts = ()=>{
    api.get('/products/').then(res=>{
      const data = res.data.results ?? res.data
      // Filter out products with stock 0
      setProducts(data.filter((p: Product) => (typeof p.stock === 'number' ? p.stock : 1) > 0))
    }).catch(console.error).finally(()=>setLoading(false))
  }

  useEffect(()=>{ fetchProducts() },[])

  // Fetch user
  useEffect(()=>{
    apiAuth.get('/auth/current-user/').then(res=> setUser(res.data)).catch(()=>setUser(null))
  },[])

  // Add product
  const handleAdd = async (e:any)=>{
    e.preventDefault()
    try{
      console.log('addForm.image:', addForm.image, 'type:', addForm.image && typeof addForm.image, 'instanceof File:', addForm.image instanceof File);
      const formData = new FormData()
      formData.append('name', addForm.name)
      formData.append('description', addForm.description)
      formData.append('price', addForm.price)
      formData.append('stock', addForm.stock)
      if (addForm.image) formData.append('image', addForm.image)
      await apiAuth.post('/products/', formData)
      setShowAdd(false)
      setAddForm({name:'', description:'', price:'', stock:'', image: null})
      fetchProducts()
    }catch(err:any){
      alert('Error adding product: '+JSON.stringify(err?.response?.data||err.message))
    }
  }

  // Delete product
  const handleDelete = async (id:number)=>{
    if(!window.confirm('Delete this product?')) return
    try{
      await apiAuth.delete(`/products/${id}/`)
      fetchProducts()
    }catch(err:any){
      alert('Error deleting: '+JSON.stringify(err?.response?.data||err.message))
    }
  }

  // Edit product (all fields)
  const handleEdit = (p: Product) => {
    setEditId(p.id)
    setEditForm({
      name: p.name,
      description: p.description,
      price: String(p.price),
      stock: String(p.stock ?? '')
    })
  }

  const handleEditSave = async (id: number) => {
    try {
      const formData = new FormData();
      formData.append('name', editForm.name);
      formData.append('description', editForm.description);
      formData.append('price', editForm.price);
      formData.append('stock', editForm.stock);
      // Optionally, add image if you support editing image as well
      // if (editForm.image) formData.append('image', editForm.image);
      await apiAuth.patch(`/products/${id}/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setEditId(null);
      setEditForm({name:'', description:'', price:'', stock:''});
      fetchProducts();
    } catch (err: any) {
      alert('Error updating: ' + JSON.stringify(err?.response?.data || err.message));
    }
  }

  const isAdmin = user && (user.is_staff || user.is_superuser)

  // Debug: log user info always
  if (user) {
    console.log('Current user object:', user)
  }

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-4">Products</h2>
      {isAdmin && (
        <div className="mb-4">
          <button className="bg-green-600 text-white px-4 py-2 rounded" onClick={()=>setShowAdd(v=>!v)}>
            {showAdd ? 'Cancel' : 'Add Product'}
          </button>
          {showAdd && (
            <form onSubmit={handleAdd} className="mt-2 space-y-2 bg-gray-100 p-4 rounded">
              <input required className="w-full border p-2" placeholder="Name" value={addForm.name} onChange={e=>setAddForm(f=>({...f, name:e.target.value}))} />
              <input required className="w-full border p-2" placeholder="Description" value={addForm.description} onChange={e=>setAddForm(f=>({...f, description:e.target.value}))} />
              <input required className="w-full border p-2" placeholder="Price in rupees" type="number" min="0" step="0.01" value={addForm.price} onChange={e=>setAddForm(f=>({...f, price:e.target.value}))} />
              <input required className="w-full border p-2" placeholder="Stock" type="number" min="0" value={addForm.stock} onChange={e=>setAddForm(f=>({...f, stock:e.target.value}))} />
              <input type="file" accept="image/*" className="w-full border p-2" onChange={e=>setAddForm(f=>({...f, image:e.target.files?.[0]||null}))} />
              <button className="bg-blue-600 text-white px-4 py-2 rounded">Add</button>
            </form>
          )}
        </div>
      )}
      {loading ? <div>Loading...</div> : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {products.map(p=> (
            <div key={p.id} className="relative">
              <ProductCard id={p.id} name={p.name} description={p.description} price={Number(p.price)} image={p.image} />
              {isAdmin && (
                <div className="absolute top-2 right-2 flex space-x-2">
                  <button className="bg-yellow-500 text-white px-2 py-1 rounded text-xs" onClick={()=>handleEdit(p)}>Edit</button>
                  <button className="bg-red-600 text-white px-2 py-1 rounded text-xs" onClick={()=>handleDelete(p.id)}>Delete</button>
                </div>
              )}
              {isAdmin && editId===p.id && (
                <div className="absolute left-2 top-10 bg-white border rounded p-2 z-10 w-72">
                  <form onSubmit={e=>{e.preventDefault();handleEditSave(p.id)}} className="space-y-2">
                    <label className="block text-xs font-semibold">Name
                      <input required className="w-full border p-1 mt-1" placeholder="Name" value={editForm.name} onChange={e=>setEditForm(f=>({...f, name:e.target.value}))} />
                    </label>
                    <label className="block text-xs font-semibold">Description
                      <input required className="w-full border p-1 mt-1" placeholder="Description" value={editForm.description} onChange={e=>setEditForm(f=>({...f, description:e.target.value}))} />
                    </label>
                    <label className="block text-xs font-semibold">Price (₹)
                      <input required className="w-full border p-1 mt-1" placeholder="Price in rupees" type="number" min="0" step="0.01" value={editForm.price} onChange={e=>setEditForm(f=>({...f, price:e.target.value}))} />
                    </label>
                    <label className="block text-xs font-semibold">Stock
                      <input required className="w-full border p-1 mt-1" placeholder="Stock" type="number" min="0" value={editForm.stock} onChange={e=>setEditForm(f=>({...f, stock:e.target.value}))} />
                    </label>
                    <div className="flex space-x-2">
                      <button className="bg-blue-600 text-white px-2 py-1 rounded text-xs" type="submit">Save</button>
                      <button className="text-xs" type="button" onClick={()=>setEditId(null)}>Cancel</button>
                    </div>
                  </form>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
