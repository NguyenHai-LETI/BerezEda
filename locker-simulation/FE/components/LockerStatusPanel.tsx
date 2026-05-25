'use client'

import { useEffect, useRef, useState } from 'react'
import { collection, onSnapshot, query } from 'firebase/firestore'
import { getFirestoreDb } from '@/lib/firebase'
import { MapPin, Wifi } from 'lucide-react'

interface LockerUnit {
  id: string
  unit_number: number
  status: string
  temperature?: number | null
  size?: string | null
  is_active?: boolean
}

interface LockerLocation {
  id: string
  name: string
  address: string
  is_active?: boolean
}

const STATUS_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  available: { bg: 'bg-green-100', text: 'text-green-700', label: 'Свободна' },
  occupied:  { bg: 'bg-red-100',   text: 'text-red-700',   label: 'Занята'   },
  reserved:  { bg: 'bg-yellow-100',text: 'text-yellow-700',label: 'Забронирована' },
  maintenance:{ bg: 'bg-gray-200', text: 'text-gray-600',  label: 'Обслуживание' },
}

function getStatusConfig(status: string) {
  return STATUS_CONFIG[status?.toLowerCase()] || STATUS_CONFIG['maintenance']
}

export default function LockerStatusPanel() {
  const [locations, setLocations] = useState<LockerLocation[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [units, setUnits] = useState<LockerUnit[]>([])
  const [connected, setConnected] = useState(false)
  const unsubLocRef = useRef<(() => void) | null>(null)
  const unsubUnitsRef = useRef<(() => void) | null>(null)

  // Listen to all locker locations
  useEffect(() => {
    try {
      const db = getFirestoreDb()
      const q = query(collection(db, 'locker_locations'))
      const unsub = onSnapshot(q, (snap) => {
        const locs: LockerLocation[] = snap.docs
          .map(d => ({ id: d.id, ...d.data() } as LockerLocation))
          .filter(l => l.is_active !== false)
          .sort((a, b) => a.name.localeCompare(b.name))
        setLocations(locs)
        setConnected(true)
        if (locs.length > 0 && !selectedId) {
          setSelectedId(locs[0].id)
        }
      }, () => setConnected(false))
      unsubLocRef.current = unsub
    } catch {
      setConnected(false)
    }
    return () => { unsubLocRef.current?.() }
  }, [])

  // Listen to units of selected location
  useEffect(() => {
    unsubUnitsRef.current?.()
    setUnits([])
    if (!selectedId) return
    try {
      const db = getFirestoreDb()
      const colRef = collection(db, 'locker_locations', selectedId, 'units')
      const unsub = onSnapshot(colRef, (snap) => {
        const data: LockerUnit[] = snap.docs
          .map(d => ({ id: d.id, ...d.data() } as LockerUnit))
          .filter(u => u.is_active !== false)
          .sort((a, b) => a.unit_number - b.unit_number)
        setUnits(data)
      })
      unsubUnitsRef.current = unsub
    } catch {}
    return () => { unsubUnitsRef.current?.() }
  }, [selectedId])

  const selectedLocation = locations.find(l => l.id === selectedId)
  const available = units.filter(u => u.status?.toLowerCase() === 'available').length

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-xl font-bold text-gray-800">Постаматы</h2>
        <Wifi className={`h-4 w-4 ${connected ? 'text-green-500' : 'text-gray-400'}`} />
        <span className={`h-2.5 w-2.5 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`} />
      </div>

      {/* Location Dropdown */}
      <div className="bg-white rounded-xl border border-gray-200 px-4 py-3 mb-4">
        <p className="text-xs text-gray-400 mb-1">Выберите постамат</p>
        <select
          value={selectedId}
          onChange={e => setSelectedId(e.target.value)}
          className="w-full text-sm font-semibold text-gray-800 bg-transparent focus:outline-none cursor-pointer"
        >
          {locations.length === 0 && <option value="">Нет данных...</option>}
          {locations.map(l => (
            <option key={l.id} value={l.id}>
              {l.name} — {l.address}
            </option>
          ))}
        </select>
      </div>

      {/* Location Card */}
      {selectedLocation && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 flex-1 flex flex-col">
          {/* Location Info */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="font-bold text-gray-900">{selectedLocation.name}</p>
              <p className="text-xs text-gray-400 flex items-center gap-1 mt-0.5">
                <MapPin className="h-3 w-3 shrink-0" />
                {selectedLocation.address}
              </p>
            </div>
            <div className="text-right shrink-0 ml-3">
              <p className="text-sm font-semibold text-gray-700">
                <span className="text-green-600">{available}</span>/{units.length}
              </p>
              <p className="text-xs text-gray-400">свободно</p>
            </div>
          </div>

          {/* Units Grid */}
          {units.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
              Нет данных по ячейкам
            </div>
          ) : (
            <>
              <div className="grid grid-cols-4 gap-2 mb-4">
                {units.map(u => {
                  const cfg = getStatusConfig(u.status)
                  return (
                    <div
                      key={u.id}
                      className={`rounded-lg border-2 ${cfg.bg} border-transparent p-2 text-center flex flex-col items-center justify-center h-[72px] transition-all`}
                      title={`#${u.unit_number} — ${cfg.label}`}
                    >
                      <span className={`text-xl font-bold ${cfg.text}`}>{u.unit_number}</span>
                      {u.temperature != null && (
                        <span className={`text-[10px] ${cfg.text} leading-tight`}>({u.temperature}°C)</span>
                      )}
                    </div>
                  )
                })}
              </div>

              {/* Legend */}
              <div className="flex flex-wrap gap-3 mt-auto pt-3 border-t border-gray-100">
                {Object.entries(STATUS_CONFIG).map(([key, cfg]) => (
                  <div key={key} className="flex items-center gap-1.5 text-xs text-gray-500">
                    <span className={`inline-block w-3 h-3 rounded ${cfg.bg}`} />
                    {cfg.label}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {locations.length === 0 && (
        <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
          Ожидание данных Firebase...
        </div>
      )}
    </div>
  )
}
