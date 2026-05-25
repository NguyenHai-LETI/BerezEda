'use client';
import { useState, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Camera, MapPin } from 'lucide-react';
import { createLockerLocation, uploadLockerImage } from '@/lib/api';
import { getPlaceSuggestions, getPlaceDetails, reverseGeocode, PlaceSuggestion } from '@/lib/google-maps';
import { GoogleMap, useJsApiLoader, MarkerF } from '@react-google-maps/api';
import Image from 'next/image';

const GOOGLE_MAPS_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY || '';
const DEFAULT_CENTER = { lat: 59.9343, lng: 30.3351 };

export default function NewLockerPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [latLng, setLatLng] = useState<{ lat: number; lng: number } | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [suggestions, setSuggestions] = useState<PlaceSuggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const mapRef = useRef<google.maps.Map | null>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const { isLoaded } = useJsApiLoader({
    googleMapsApiKey: GOOGLE_MAPS_KEY,
    language: 'ru',
  });

  const onMapLoad = useCallback((map: google.maps.Map) => {
    mapRef.current = map;
  }, []);

  // Address input with debounced autocomplete
  function handleAddressInput(value: string) {
    setAddress(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (value.length < 2) { setSuggestions([]); setShowSuggestions(false); return; }
    debounceRef.current = setTimeout(async () => {
      const results = await getPlaceSuggestions(value);
      setSuggestions(results);
      setShowSuggestions(results.length > 0);
    }, 300);
  }

  // Select suggestion
  async function handleSelectSuggestion(s: PlaceSuggestion) {
    setShowSuggestions(false);
    setAddress(s.description);
    const detail = await getPlaceDetails(s.place_id);
    if (detail) {
      setLatLng({ lat: detail.lat, lng: detail.lng });
      setAddress(detail.address);
      mapRef.current?.panTo({ lat: detail.lat, lng: detail.lng });
      mapRef.current?.setZoom(16);
    }
  }

  // Click on map → reverse geocode
  async function handleMapClick(e: google.maps.MapMouseEvent) {
    if (!e.latLng) return;
    const pos = { lat: e.latLng.lat(), lng: e.latLng.lng() };
    setLatLng(pos);
    const addr = await reverseGeocode(pos.lat, pos.lng);
    if (addr) setAddress(addr);
  }

  function handleImageChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!latLng) {
      setError('Выберите адрес из предложений или укажите точку на карте');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const res = await createLockerLocation({
        name,
        address,
        latitude: latLng.lat,
        longitude: latLng.lng,
        unit_count: 0,
      });
      const id = res?.data?.id;
      if (id && imageFile) await uploadLockerImage(id, imageFile);
      router.push(id ? `/locker-owner/lockers/${id}` : '/locker-owner/lockers');
    } catch (err: any) {
      setError(err?.message || 'Ошибка при создании постамата');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto py-6 px-4">
      <h1 className="text-2xl font-bold mb-6">Новый постамат</h1>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border p-6 space-y-5">
        {/* Image */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Фото постамата</label>
          {imagePreview ? (
            <div className="relative w-full h-48 rounded-xl overflow-hidden border">
              <Image src={imagePreview} alt="Preview" fill className="object-cover" />
              <button
                type="button"
                onClick={() => { setImageFile(null); setImagePreview(null); }}
                className="absolute top-2 right-2 bg-white/90 rounded-full w-7 h-7 flex items-center justify-center text-sm text-red-500 hover:bg-white shadow"
              >
                ✕
              </button>
            </div>
          ) : (
            <label className="flex flex-col items-center justify-center w-full h-48 rounded-xl border-2 border-dashed border-gray-300 cursor-pointer hover:border-blue-400 transition-colors bg-gray-50">
              <Camera className="h-10 w-10 text-gray-300 mb-2" aria-hidden="true" />
              <span className="text-sm text-gray-400">Нажмите, чтобы выбрать фото</span>
              <input type="file" accept="image/*" className="hidden" onChange={handleImageChange} />
            </label>
          )}
        </div>

        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Название</label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="Постамат у метро Тверская"
          />
        </div>

        {/* Address with autocomplete */}
        <div className="relative">
          <label className="block text-sm font-medium text-gray-700 mb-1">Адрес</label>
          <input
            required
            value={address}
            onChange={(e) => handleAddressInput(e.target.value)}
            onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            className="w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="Начните вводить адрес..."
          />
          {showSuggestions && suggestions.length > 0 && (
            <ul className="absolute z-20 w-full bg-white border rounded-lg mt-1 shadow-lg max-h-48 overflow-y-auto">
              {suggestions.map((s) => (
                <li
                  key={s.place_id}
                  onMouseDown={() => handleSelectSuggestion(s)}
                  className="px-3 py-2 text-sm hover:bg-yellow-50 cursor-pointer border-b last:border-b-0"
                >
                  {s.description}
                </li>
              ))}
            </ul>
          )}
          {latLng && (
            <p className="text-xs text-green-600 mt-1">
              <MapPin className="h-3 w-3 inline" aria-hidden="true" /> {latLng.lat.toFixed(6)}, {latLng.lng.toFixed(6)}
            </p>
          )}
          {!latLng && address.length > 0 && (
            <p className="text-xs text-yellow-600 mt-1">
              Выберите адрес из списка или укажите на карте
            </p>
          )}
        </div>

        {/* Map */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Расположение на карте</label>
          <div className="h-64 rounded-xl overflow-hidden border border-gray-200">
            {!GOOGLE_MAPS_KEY || !isLoaded ? (
              <div className="flex items-center justify-center h-full bg-gray-100 text-gray-400 text-sm">Загрузка карты...</div>
            ) : (
              <GoogleMap
                mapContainerStyle={{ width: '100%', height: '100%' }}
                center={latLng || DEFAULT_CENTER}
                zoom={latLng ? 16 : 12}
                onLoad={onMapLoad}
                onClick={handleMapClick}
                options={{ streetViewControl: false, mapTypeControl: false, fullscreenControl: false }}
              >
                {latLng && <MarkerF position={latLng} />}
              </GoogleMap>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-1">Нажмите на карту, чтобы указать расположение постамата</p>
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <div className="flex gap-3 pt-2">
          <button type="button" onClick={() => router.back()} className="flex-1 border rounded-lg py-2 text-sm font-medium hover:bg-gray-50">
            Отмена
          </button>
          <button type="submit" disabled={saving} className="flex-1 bg-indigo-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">
            {saving ? 'Создание...' : 'Создать'}
          </button>
        </div>
      </form>
    </div>
  );
}
