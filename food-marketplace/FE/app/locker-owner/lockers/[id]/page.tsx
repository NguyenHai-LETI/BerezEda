'use client';
import { useEffect, useRef, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Image from 'next/image';
import { Package, Camera, Pencil, MapPin, Upload, LocateFixed } from 'lucide-react';
import ConfirmModal from '@/components/ConfirmModal';
import {
  getLockerLocation, getLockerUnits, createLockerUnit, deleteLockerUnit,
  getLockerShops, getShops, addShopToLocker, importLockerUnitsCsv,
  updateLockerLocation, uploadLockerImage,
} from '@/lib/api';
import { getPlaceSuggestions, getPlaceDetails, reverseGeocode, PlaceSuggestion } from '@/lib/google-maps';
import { GoogleMap, useJsApiLoader, MarkerF } from '@react-google-maps/api';

const GOOGLE_MAPS_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY || '';
const DEFAULT_CENTER = { lat: 59.9343, lng: 30.3351 };
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
const IMG_BASE = API_URL.replace(/\/api\/?$/, '');

interface LockerUnit {
  id: string;
  unit_number: number;
  status: string;
  temperature?: number;
  size?: string;
}

interface Shop { id: string; name: string; }

const STATUS_LABEL: Record<string, string> = {
  AVAILABLE: 'Свободна', RESERVED: 'Зарезервирована',
  OCCUPIED: 'Занята', MAINTENANCE: 'Обслуживание',
};
const STATUS_COLOR: Record<string, string> = {
  AVAILABLE:   'bg-green-100 text-green-700',
  RESERVED:    'bg-yellow-100 text-yellow-700',
  OCCUPIED:    'bg-red-100 text-red-700',
  MAINTENANCE: 'bg-gray-100 text-gray-600',
};

export default function LockerDetailPage() {
  const params = useParams();
  const locationId = params.id as string;
  const [location, setLocation] = useState<any>(null);
  const [units, setUnits] = useState<LockerUnit[]>([]);
  const [attachedShops, setAttachedShops] = useState<Shop[]>([]);
  const [allShops, setAllShops] = useState<Shop[]>([]);
  const [loading, setLoading] = useState(true);
  const [addingUnit, setAddingUnit] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [shopToAdd, setShopToAdd] = useState('');
  const [addingShop, setAddingShop] = useState(false);
  const [shopMsg, setShopMsg] = useState('');
  const [shopsLoadError, setShopsLoadError] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importMsg, setImportMsg] = useState('');
  const csvRef = useRef<HTMLInputElement>(null);

  // Edit mode
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [editAddress, setEditAddress] = useState('');
  const [editLatLng, setEditLatLng] = useState<{ lat: number; lng: number } | null>(null);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState('');
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [locating, setLocating] = useState(false);

  const mapRef = useRef<google.maps.Map | null>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const { isLoaded } = useJsApiLoader({ googleMapsApiKey: GOOGLE_MAPS_KEY, language: 'ru' });

  const onMapLoad = useCallback((map: google.maps.Map) => { mapRef.current = map; }, []);

  async function load() {
    setShopsLoadError(false);
    const [loc, u, shops, allShopsRes] = await Promise.all([
      getLockerLocation(locationId), getLockerUnits(locationId), getLockerShops(locationId),
      getShops().catch(() => { setShopsLoadError(true); return null; }),
    ]);
    setLocation(loc?.data || null);
    setUnits(u?.data || []);
    setAttachedShops(shops?.data || []);
    setAllShops(allShopsRes?.data || []);
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, [locationId]);

  // --- Edit ---
  function startEdit() {
    if (!location) return;
    setEditName(location.name);
    setEditAddress(location.address || '');
    setEditLatLng(location.latitude && location.longitude ? { lat: location.latitude, lng: location.longitude } : null);
    setEditError('');
    setEditing(true);
  }

  function handleEditAddressInput(value: string) {
    setEditAddress(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (value.length < 2) { setSuggestions([]); setShowSuggestions(false); return; }
    debounceRef.current = setTimeout(async () => {
      const results = await getPlaceSuggestions(value);
      setSuggestions(results);
      setShowSuggestions(results.length > 0);
    }, 300);
  }

  async function handleEditSelectSuggestion(s: PlaceSuggestion) {
    setShowSuggestions(false);
    setEditAddress(s.description);
    const detail = await getPlaceDetails(s.place_id);
    if (detail) {
      setEditLatLng({ lat: detail.lat, lng: detail.lng });
      setEditAddress(detail.address);
      mapRef.current?.panTo({ lat: detail.lat, lng: detail.lng });
      mapRef.current?.setZoom(16);
    }
  }

  function handleLocateMe() {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      pos => {
        const { latitude: lat, longitude: lng } = pos.coords;
        setEditLatLng({ lat, lng });
        mapRef.current?.panTo({ lat, lng });
        mapRef.current?.setZoom(16);
        reverseGeocode(lat, lng).then(addr => { if (addr) setEditAddress(addr); });
        setLocating(false);
      },
      () => setLocating(false),
      { timeout: 8000, maximumAge: 30000 }
    );
  }

  function handleEditMapClick(e: google.maps.MapMouseEvent) {
    if (!e.latLng) return;
    const pos = { lat: e.latLng.lat(), lng: e.latLng.lng() };
    setEditLatLng(pos);
    mapRef.current?.panTo(pos);
    // Google Geocoding API requires billing — use Nominatim (free) via server route
    reverseGeocode(pos.lat, pos.lng).then(addr => { if (addr) setEditAddress(addr); });
  }

  async function handleEditSave() {
    if (!editLatLng) { setEditError('Выберите адрес из предложений или укажите на карте'); return; }
    setEditSaving(true); setEditError('');
    try {
      await updateLockerLocation(locationId, {
        name: editName, address: editAddress,
        latitude: editLatLng.lat, longitude: editLatLng.lng,
      });
      setEditing(false);
      await load();
    } catch (err: any) {
      setEditError(err?.message || 'Ошибка сохранения');
    } finally { setEditSaving(false); }
  }

  // --- Image ---
  async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingImage(true);
    try { await uploadLockerImage(locationId, file); await load(); }
    catch (err: any) { alert(err.message || 'Ошибка загрузки фото'); }
    finally { setUploadingImage(false); e.target.value = ''; }
  }

  // --- Units ---
  async function handleAddUnit() {
    setAddingUnit(true);
    try { await createLockerUnit(locationId, {}); await load(); } finally { setAddingUnit(false); }
  }

  async function handleDeleteUnit(unitId: string) {
    setDeletingId(unitId);
    try { await deleteLockerUnit(locationId, unitId); setUnits(prev => prev.filter(u => u.id !== unitId)); }
    finally { setDeletingId(null); }
  }

  // --- Shop ---
  async function handleAddShop() {
    if (!shopToAdd) return;
    setAddingShop(true); setShopMsg('');
    try {
      await addShopToLocker(locationId, shopToAdd);
      setShopMsg('Магазин добавлен'); setShopToAdd('');
      const shops = await getLockerShops(locationId);
      setAttachedShops(shops?.data || []);
    } catch (e: any) { setShopMsg(e.message || 'Ошибка'); }
    finally { setAddingShop(false); }
  }

  // --- CSV ---
  async function handleCsvImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true); setImportMsg('');
    try {
      const res = await importLockerUnitsCsv(locationId, file);
      setImportMsg(`Импортировано: ${res?.data?.created ?? 0} ячеек`);
      await load();
    } catch (err: any) { setImportMsg(err.message || 'Ошибка импорта'); }
    finally { setImporting(false); if (csvRef.current) csvRef.current.value = ''; }
  }

  if (loading) return <div className="p-6 text-gray-500">Загрузка...</div>;
  if (!location) return <div className="p-6 text-red-500">Постамат не найден</div>;

  const available = units.filter(u => u.status === 'AVAILABLE').length;
  const occupied = units.filter(u => u.status === 'OCCUPIED' || u.status === 'RESERVED').length;
  const attachedShopIds = new Set(attachedShops.map(s => s.id));
  const unattachedShops = allShops.filter(s => !attachedShopIds.has(s.id));
  const lockerImgUrl = location.image
    ? (location.image.startsWith('http') ? location.image : `${IMG_BASE}/uploads/${location.image.replace(/^\//, '')}`)
    : null;

  return (
    <div className="max-w-2xl mx-auto py-6 px-4 space-y-6">

      {/* ═══════════════ SECTION 1: Locker Info ═══════════════ */}
      <div className="bg-white rounded-xl border overflow-hidden shadow-sm">
        {/* Image */}
        <div className="relative h-72 bg-gray-100">
          {lockerImgUrl ? (
            <Image src={lockerImgUrl} alt={location.name} fill className="object-cover" />
          ) : (
            <div className="flex items-center justify-center h-full"><Package className="h-10 w-10 text-gray-300" aria-hidden="true" /></div>
          )}
          <label className={`absolute bottom-3 right-3 bg-white/90 rounded-lg px-3 py-1.5 text-xs font-medium cursor-pointer hover:bg-white shadow transition ${uploadingImage ? 'opacity-50 pointer-events-none' : ''}`}>
            <span className="flex items-center gap-1">{uploadingImage ? 'Загрузка...' : <><Camera className="h-3 w-3" aria-hidden="true" /> Изменить фото</>}</span>
            <input type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
          </label>
        </div>

        <div className="p-4">
          {!editing ? (
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-2xl font-bold mb-1">{location.name}</h1>
                <p className="text-gray-500 text-sm">{location.address}</p>
                {location.latitude && location.longitude && (
                  <p className="text-xs text-gray-400 mt-1"><MapPin className="h-3 w-3 inline" aria-hidden="true" /> {location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}</p>
                )}
              </div>
              <button onClick={startEdit} className="text-sm text-indigo-600 hover:text-indigo-800 font-medium">
                <span className="flex items-center gap-1"><Pencil className="h-3 w-3" aria-hidden="true" /> Редактировать</span>
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Название</label>
                <input value={editName} onChange={e => setEditName(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="relative">
                <label className="block text-sm font-medium text-gray-700 mb-1">Адрес</label>
                <input
                  value={editAddress}
                  onChange={e => handleEditAddressInput(e.target.value)}
                  onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  placeholder="Начните вводить адрес..."
                />
                {showSuggestions && suggestions.length > 0 && (
                  <ul className="absolute z-20 w-full bg-white border rounded-lg mt-1 shadow-lg max-h-48 overflow-y-auto">
                    {suggestions.map(s => (
                      <li key={s.place_id} onMouseDown={() => handleEditSelectSuggestion(s)}
                        className="px-3 py-2 text-sm hover:bg-yellow-50 cursor-pointer border-b last:border-b-0">
                        {s.description}
                      </li>
                    ))}
                  </ul>
                )}
                {editLatLng && (
                  <p className="text-xs text-green-600 mt-1"><MapPin className="h-3 w-3 inline" aria-hidden="true" /> {editLatLng.lat.toFixed(6)}, {editLatLng.lng.toFixed(6)}</p>
                )}
              </div>
              <div className="relative h-80 rounded-xl overflow-hidden border">
                {isLoaded ? (
                  <GoogleMap
                    mapContainerStyle={{ width: '100%', height: '100%' }}
                    center={editLatLng || DEFAULT_CENTER} zoom={editLatLng ? 16 : 12}
                    onLoad={onMapLoad} onClick={handleEditMapClick}
                    options={{ streetViewControl: false, mapTypeControl: false, fullscreenControl: false, clickableIcons: false }}
                  >
                    {editLatLng && <MarkerF position={editLatLng} />}
                  </GoogleMap>
                ) : (
                  <div className="flex items-center justify-center h-full bg-gray-100 text-gray-400 text-sm">Загрузка...</div>
                )}
                <button
                  onClick={handleLocateMe}
                  disabled={locating}
                  title="Моё местоположение"
                  className="absolute bottom-24 right-2 z-10 bg-white rounded shadow-md w-8 h-8 flex items-center justify-center hover:bg-gray-50 disabled:opacity-50 transition-colors"
                >
                  <LocateFixed className={`h-4 w-4 ${locating ? 'text-indigo-400 animate-pulse' : 'text-gray-600'}`} />
                </button>
              </div>
              {editError && <p className="text-red-500 text-sm">{editError}</p>}
              <div className="flex gap-2">
                <button onClick={() => setEditing(false)} className="flex-1 border rounded-lg py-2 text-sm hover:bg-gray-50">Отмена</button>
                <button onClick={handleEditSave} disabled={editSaving} className="flex-1 bg-indigo-600 text-white rounded-lg py-2 text-sm hover:bg-indigo-700 disabled:opacity-50">
                  {editSaving ? 'Сохранение...' : 'Сохранить'}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Stats inside info card */}
        <div className="border-t grid grid-cols-3 divide-x">
          <div className="p-4 text-center">
            <p className="text-2xl font-bold text-gray-900">{units.length}</p>
            <p className="text-xs text-gray-500 mt-1">Всего ячеек</p>
          </div>
          <div className="p-4 text-center">
            <p className="text-2xl font-bold text-green-600">{available}</p>
            <p className="text-xs text-gray-500 mt-1">Свободных</p>
          </div>
          <div className="p-4 text-center">
            <p className="text-2xl font-bold text-blue-600">{occupied}</p>
            <p className="text-xs text-gray-500 mt-1">Занятых</p>
          </div>
        </div>
      </div>

      {/* ═══════════════ SECTION 2: Shops ═══════════════ */}
      <div className="bg-white rounded-xl border p-4 shadow-sm">
        <h2 className="text-base font-semibold mb-3">Магазины в постамате</h2>
        {attachedShops.length === 0 ? (
          <p className="text-sm text-gray-400 mb-3">Нет подключённых магазинов</p>
        ) : (
          <div className="flex flex-wrap gap-2 mb-3">
            {attachedShops.map(s => (
              <span key={s.id} className="bg-indigo-50 text-indigo-700 text-xs px-3 py-1 rounded-full border border-indigo-200">{s.name}</span>
            ))}
          </div>
        )}
        {shopsLoadError ? (
          <p className="text-sm text-red-500 mb-2">Не удалось загрузить список магазинов</p>
        ) : (
          <div className="flex gap-2">
            <select value={shopToAdd} onChange={e => setShopToAdd(e.target.value)} className="flex-1 border rounded-lg px-3 py-2 text-sm">
              <option value="">Выберите магазин...</option>
              {unattachedShops.map(s => (<option key={s.id} value={s.id}>{s.name}</option>))}
            </select>
            <button onClick={handleAddShop} disabled={!shopToAdd || addingShop} className="bg-indigo-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50">
              {addingShop ? '...' : 'Добавить'}
            </button>
          </div>
        )}
        {shopMsg && <p className="text-sm mt-2 text-green-600">{shopMsg}</p>}
      </div>

      {/* ═══════════════ SECTION 3: Units (separated) ═══════════════ */}
      <div className="bg-white rounded-xl border p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Ячейки</h2>
          <div className="flex gap-2">
            <label className={`cursor-pointer border text-sm px-3 py-1.5 rounded-lg hover:bg-gray-50 ${importing ? 'opacity-50 pointer-events-none' : ''}`}>
              <span className="flex items-center gap-1">{importing ? 'Импорт...' : <><Upload className="h-3 w-3" aria-hidden="true" /> CSV</>}</span>
              <input ref={csvRef} type="file" accept=".csv" className="hidden" onChange={handleCsvImport} />
            </label>
            <button onClick={handleAddUnit} disabled={addingUnit} className="bg-indigo-600 text-white text-sm px-3 py-1.5 rounded-lg hover:bg-indigo-700 disabled:opacity-50">
              {addingUnit ? '...' : '+ Ячейка'}
            </button>
          </div>
        </div>

        {importMsg && <p className={`text-sm mb-2 ${importMsg.includes('Ошибка') ? 'text-red-500' : 'text-green-600'}`}>{importMsg}</p>}
        <p className="text-xs text-gray-400 mb-3">
          CSV: <code>unit_number,size,temperature</code> (size, temperature — опционально).
          Если ячейка с таким номером уже существует — она будет пропущена.
        </p>

        {units.length === 0 ? (
          <p className="text-gray-400 text-center py-8">Нет ячеек. Импортируйте CSV или добавьте вручную.</p>
        ) : (
          <div className="space-y-2">
            {units.map(unit => (
              <div key={unit.id} className="bg-gray-50 rounded-xl border p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-gray-400 text-sm w-8 text-right font-mono">#{unit.unit_number}</span>
                  <span className={`text-xs px-2 py-1 rounded-full ${STATUS_COLOR[unit.status] || 'bg-gray-100 text-gray-500'}`}>
                    {STATUS_LABEL[unit.status] || unit.status}
                  </span>
                  {unit.size && <span className="text-xs text-gray-400">{unit.size}</span>}
                  {unit.temperature != null && <span className="text-xs text-blue-500">{unit.temperature}°C</span>}
                </div>
                {unit.status === 'AVAILABLE' && (
                  <button onClick={() => setDeleteConfirmId(unit.id)} disabled={deletingId === unit.id}
                    className="text-xs text-red-400 hover:text-red-600 disabled:opacity-50">
                    {deletingId === unit.id ? '...' : 'Удалить'}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <ConfirmModal
        open={!!deleteConfirmId}
        title="Удалить ячейку?"
        message="Ячейка будет удалена из постамата. Это действие нельзя отменить."
        confirmText="Да, удалить"
        onConfirm={() => { if (deleteConfirmId) { handleDeleteUnit(deleteConfirmId); setDeleteConfirmId(null); } }}
        onCancel={() => setDeleteConfirmId(null)}
      />
    </div>
  );
}
