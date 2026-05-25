'use client'

import dynamic from 'next/dynamic'

const LockerStatusPanel = dynamic(() => import('@/components/LockerStatusPanel'), { ssr: false })
const LockerSimulator = dynamic(() => import('@/components/LockerSimulator'), { ssr: false })

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* Top bar */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-green-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">LS</span>
          </div>
          <div>
            <h1 className="text-base font-bold text-gray-900">Locker Simulation System</h1>
            <p className="text-xs text-gray-400">Система моделирования постамата — Realtime Firebase</p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span className="bg-blue-50 text-blue-600 px-2 py-1 rounded font-mono">BE :8001</span>
          <span className="bg-green-50 text-green-600 px-2 py-1 rounded font-mono">FE :3001</span>
        </div>
      </header>

      {/* Main layout */}
      <main className="flex-1 flex gap-0 overflow-hidden" style={{ height: 'calc(100vh - 57px)' }}>
        {/* Left: Locker Status (Firebase realtime) */}
        <div className="w-1/2 p-4 overflow-y-auto border-r border-gray-200 bg-gray-50">
          <LockerStatusPanel />
        </div>

        {/* Right: Locker Simulator */}
        <div className="w-1/2 p-4 overflow-y-auto bg-white">
          <LockerSimulator />
        </div>
      </main>
    </div>
  )
}
