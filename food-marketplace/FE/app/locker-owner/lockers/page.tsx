'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getMyLockerLocations } from '@/lib/api';

interface LockerLocation {
  id: string;
  name: string;
  address: string;
  is_active: boolean;
  total_units?: number;
}

export default function LockersPage() {
  const [lockers, setLockers] = useState<LockerLocation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMyLockerLocations()
      .then((r: any) => setLockers(r?.data || []))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-2xl mx-auto py-6 px-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Мои постаматы</h1>
        <Link
          href="/locker-owner/lockers/new"
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700"
        >
          + Добавить
        </Link>
      </div>

      {loading && <p className="text-gray-500">Загрузка...</p>}

      {!loading && lockers.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg">У вас нет постаматов</p>
          <Link href="/locker-owner/lockers/new" className="mt-4 inline-block text-indigo-600 underline">
            Добавить первый постамат
          </Link>
        </div>
      )}

      <div className="space-y-3">
        {lockers.map((loc) => (
          <Link
            key={loc.id}
            href={`/locker-owner/lockers/${loc.id}`}
            className="block bg-white rounded-xl shadow-sm border p-4 hover:shadow-md transition"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="font-semibold text-gray-900">{loc.name}</p>
                <p className="text-sm text-gray-500 mt-1">{loc.address}</p>
                {loc.total_units !== undefined && (
                  <p className="text-sm text-gray-400 mt-1">Ячеек: {loc.total_units}</p>
                )}
              </div>
              <span
                className={`text-xs px-2 py-1 rounded-full ${
                  loc.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                }`}
              >
                {loc.is_active ? 'Активен' : 'Неактивен'}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
