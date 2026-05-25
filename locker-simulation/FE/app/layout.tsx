import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Locker Simulation',
  description: 'Hệ thống mô phỏng tủ locker',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body className="bg-gray-100 min-h-screen">{children}</body>
    </html>
  )
}
