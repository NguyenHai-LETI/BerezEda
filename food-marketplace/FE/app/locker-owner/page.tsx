'use client'
import { useEffect, useState } from 'react'
import { getMyLockerLocations, deleteLockerLocation } from '@/lib/api'
import Link from 'next/link'
import Image from 'next/image'
import { Package } from 'lucide-react'
import ConfirmModal from '@/components/ConfirmModal'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
const IMG_BASE = API_URL.replace(/\/api\/?$/, '')

export default function LockerOwnerDashboard() {
  const [lockers, setLockers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState<any>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')

  useEffect(() => {
    loadLockers()
  }, [])

  async function loadLockers() {
    try {
      const r = await getMyLockerLocations()
      setLockers(r.data || [])
    } catch {
      setLockers([])
    } finally {
      setLoading(false)
    }
  }

  const totalUnits = lockers.reduce((s: number, l: any) => s + (l.units?.length || 0), 0)
  const occupiedUnits = lockers.reduce((s: number, l: any) =>
    s + (l.units?.filter((u: any) => u.status === 'OCCUPIED' || u.status === 'RESERVED').length || 0), 0)

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    setDeleteError('')
    try {
      await deleteLockerLocation(deleteTarget.id)
      setDeleteTarget(null)
      await loadLockers()
    } catch (err: any) {
      setDeleteError(err?.message || 'Ошибка удаления')
    } finally {
      setDeleting(false)
    }
  }

  function imgUrl(loc: any) {
    if (!loc.image) return null
    return loc.image.startsWith('http') ? loc.image : `${IMG_BASE}/uploads/${loc.image.replace(/^\//, '')}`
  }

  return (
    <div className="max-w-2xl mx-auto p-4">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">Панель управления</h1>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"/>
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="grid grid-cols-3 gap-3 mb-6">
            <div className="bg-white rounded-xl border border-gray-100 p-4 text-center">
              <p className="text-2xl font-bold text-blue-500">{lockers.length}</p>
              <p className="text-xs text-gray-500 mt-1">Постаматов</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-100 p-4 text-center">
              <p className="text-2xl font-bold text-green-500">{totalUnits}</p>
              <p className="text-xs text-gray-500 mt-1">Всего ячеек</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-100 p-4 text-center">
              <p className="text-2xl font-bold text-orange-500">{occupiedUnits}</p>
              <p className="text-xs text-gray-500 mt-1">Занято</p>
            </div>
          </div>

          {/* Quick actions */}
          <div className="flex gap-3 mb-6">
            <Link href="/locker-owner/lockers/new"
              className="flex-1 bg-blue-500 hover:bg-blue-600 text-white font-medium py-3 rounded-xl text-center text-sm transition">
              + Добавить постамат
            </Link>
            <Link href="/locker-owner/lockers"
              className="flex-1 border-2 border-blue-200 text-blue-600 font-medium py-3 rounded-xl text-center text-sm transition hover:bg-blue-50">
              Все постаматы
            </Link>
          </div>

          {/* Lockers list */}
          {lockers.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Package className="h-10 w-10 text-gray-300 mx-auto mb-2" aria-hidden="true" />
              <p>У вас ещё нет постаматов</p>
              <Link href="/locker-owner/lockers/new"
                className="inline-block mt-4 bg-blue-500 text-white px-6 py-2 rounded-xl text-sm">
                Добавить первый
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {lockers.map((l: any) => (
                <div key={l.id} className="bg-white rounded-xl border border-gray-100 overflow-hidden hover:shadow-md transition">
                  <Link href={`/locker-owner/lockers/${l.id}`}>
                    <div className="flex">
                      {/* Image */}
                      <div className="w-24 h-24 flex-shrink-0 bg-gray-100 relative">
                        {imgUrl(l) ? (
                          <Image src={imgUrl(l)!} alt={l.name} fill className="object-cover" />
                        ) : (
                          <div className="flex items-center justify-center h-full"><Package className="h-6 w-6 text-gray-300" aria-hidden="true" /></div>
                        )}
                      </div>
                      {/* Info */}
                      <div className="flex-1 p-3 min-w-0">
                        <p className="font-semibold text-gray-800 truncate">{l.name}</p>
                        <p className="text-xs text-gray-400 mt-0.5 truncate">{l.address}</p>
                        <div className="flex items-center gap-3 mt-2">
                          <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
                            {l.units?.length || 0} ячеек
                          </span>
                          <span className="text-xs bg-green-50 text-green-600 px-2 py-0.5 rounded-full">
                            {l.units?.filter((u: any) => u.status === 'AVAILABLE').length || 0} свободных
                          </span>
                        </div>
                      </div>
                    </div>
                  </Link>
                  {/* Delete button */}
                  <div className="border-t px-3 py-2 flex justify-end">
                    <button
                      onClick={(e) => { e.preventDefault(); setDeleteTarget(l); setDeleteError(''); }}
                      className="text-xs text-red-400 hover:text-red-600"
                    >
                      Удалить
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      <ConfirmModal
        open={!!deleteTarget}
        title="Удалить постамат?"
        message={
          deleteError
            ? deleteError
            : `Вы уверены, что хотите удалить «${deleteTarget?.name}»? Все ячейки будут удалены.`
        }
        confirmText={deleting ? 'Удаление...' : 'Да, удалить'}
        onConfirm={handleDelete}
        onCancel={() => { setDeleteTarget(null); setDeleteError(''); }}
      />
    </div>
  )
}
