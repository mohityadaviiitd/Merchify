import { useEffect, useState } from 'react'
import api from '../lib/api_with_auth'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend } from 'chart.js'
import { Line, Bar } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend)

export default function AdminDashboard(){
  const [stats, setStats] = useState<any>(null)
  const [error, setError] = useState('')

  useEffect(()=>{
    api.get('/dashboard/stats/').then(res=> setStats(res.data)).catch(err=> setError('Access denied or login required'))
  },[])

  if(error) return <div className="p-6">{error}</div>

  if(!stats) return <div className="p-6">Loading...</div>

  const revenueData = {
    labels: stats.revenue_trend.map((r:any)=> r.date),
    datasets: [{ label: 'Revenue', data: stats.revenue_trend.map((r:any)=> r.revenue), borderColor: 'rgb(75,192,192)', backgroundColor: 'rgba(75,192,192,0.2)'}]
  }

  const topProducts = {
    labels: stats.top_products.map((p:any)=> p.name),
    datasets: [{ label: 'Units Sold', data: stats.top_products.map((p:any)=> p.total_sold || 0), backgroundColor: 'rgba(53,162,235,0.5)'}]
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-4">Admin Dashboard</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="p-4 border rounded">Total Products<br/><span className="font-semibold text-xl">{stats.total_products}</span></div>
        <div className="p-4 border rounded">Total Users<br/><span className="font-semibold text-xl">{stats.total_users}</span></div>
        <div className="p-4 border rounded">Total Revenue<br/><span className="font-semibold text-xl">${stats.total_revenue}</span></div>
      </div>

      <div className="mb-6">
        <h3 className="font-semibold mb-2">Revenue (last 7 days)</h3>
        <Line data={revenueData} />
      </div>

      <div>
        <h3 className="font-semibold mb-2">Top Products</h3>
        <Bar data={topProducts} />
      </div>
    </div>
  )
}
