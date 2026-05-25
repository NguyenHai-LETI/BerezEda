'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getUser } from '@/lib/auth'
import { BottomNav } from '@/components/BottomNav'
import { SidebarNav } from '@/components/SidebarNav'
import { CustomerTopbar } from '@/components/CustomerTopbar'

export default function ShellLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [ready, setReady] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  useEffect(() => {
    const user = getUser()
    if (!user) {
      router.replace('/login')
      return
    }
    if (user.role === 'owner_shop') { router.replace('/seller'); return }
    if (user.role === 'owner_locker') { router.replace('/locker-owner'); return }
    setReady(true)
  }, [])

  if (!ready) return (
    <div className="flex items-center justify-center h-screen bg-bg">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  )

  return (
    <div className="flex min-h-screen bg-bg">
      <SidebarNav collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(c => !c)} />
      <main className={`flex-1 pb-14 lg:pb-0 flex flex-col min-h-screen transition-[margin] duration-200 ${sidebarCollapsed ? 'lg:ml-[72px]' : 'lg:ml-64'}`}>
        <CustomerTopbar />
        <div className="flex-1">
          {children}
        </div>
      </main>
      <div className="lg:hidden">
        <BottomNav />
      </div>
    </div>
  )
}
