import '../styles/globals.css'
import type { AppProps } from 'next/app'
import NavBar from '../components/NavBar'

export default function MyApp({ Component, pageProps }: AppProps) {
  return (
    <>
      <NavBar />
      <main className="container mx-auto px-4 py-6">
        <Component {...pageProps} />
      </main>
    </>
  )
}
