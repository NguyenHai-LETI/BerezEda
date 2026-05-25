"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { MapPin, Navigation, Loader2, MapPinOff } from "lucide-react";
import { getLockers } from "@/lib/api";
import {
  GoogleMap,
  useJsApiLoader,
  MarkerF,
  InfoWindowF,
} from "@react-google-maps/api";

const GOOGLE_MAPS_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY || "";
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

const DEFAULT_CENTER = { lat: 59.9343, lng: 30.3351 };
const DEFAULT_ZOOM = 12;

interface LockerLocation {
  id: string;
  name: string;
  address: string;
  image?: string | null;
  latitude: number | null;
  longitude: number | null;
  units: { id: string; status: string }[];
  distance_km: number | null;
}

export default function MapPage() {
  const [lockers, setLockers] = useState<LockerLocation[]>([]);
  const [userPos, setUserPos] = useState<{ lat: number; lng: number } | null>(null);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedLocker, setSelectedLocker] = useState<LockerLocation | null>(null);
  const [focusedLockerId, setFocusedLockerId] = useState<string | null>(null);
  const [mapCenter, setMapCenter] = useState(DEFAULT_CENTER);
  const [mapZoom, setMapZoom] = useState(DEFAULT_ZOOM);
  const [showGeoModal, setShowGeoModal] = useState(false);
  const [geoBannerVisible, setGeoBannerVisible] = useState(true);
  const mapRef = useRef<google.maps.Map | null>(null);
  const pageTopRef = useRef<HTMLDivElement>(null);

  const { isLoaded } = useJsApiLoader({ googleMapsApiKey: GOOGLE_MAPS_KEY });

  useEffect(() => {
    if (!navigator.geolocation) {
      setGeoError("Геолокация не поддерживается вашим браузером");
      loadLockers();
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const pos = { lat: position.coords.latitude, lng: position.coords.longitude };
        setUserPos(pos);
        setMapCenter(pos);
        loadLockers(pos.lat, pos.lng);
      },
      (err) => {
        switch (err.code) {
          case err.PERMISSION_DENIED:
            setGeoError("Разрешите доступ к геолокации для определения ближайших постаматов"); break;
          case err.POSITION_UNAVAILABLE:
            setGeoError("Информация о местоположении недоступна"); break;
          case err.TIMEOUT:
            setGeoError("Время запроса геолокации истекло"); break;
        }
        loadLockers();
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 }
    );
  }, []);

  async function loadLockers(lat?: number, lng?: number) {
    try {
      const params: { lat?: number; lon?: number } = {};
      if (lat !== undefined && lng !== undefined) { params.lat = lat; params.lon = lng; }
      const res = await getLockers(params);
      setLockers(res.data || []);
    } catch {}
    finally { setLoading(false); }
  }

  const onMapLoad = useCallback((map: google.maps.Map) => { mapRef.current = map; }, []);

  function focusLocker(locker: LockerLocation) {
    if (locker.latitude && locker.longitude && mapRef.current) {
      mapRef.current.panTo({ lat: locker.latitude, lng: locker.longitude });
      mapRef.current.setZoom(16);
      setSelectedLocker(locker);
      setFocusedLockerId(locker.id);
      pageTopRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }

  function disableGeolocation() {
    setUserPos(null); setGeoError(null);
    setMapCenter(DEFAULT_CENTER); setMapZoom(DEFAULT_ZOOM);
    loadLockers(); setShowGeoModal(false);
  }

  function retryGeolocation() {
    setGeoError(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const pos = { lat: position.coords.latitude, lng: position.coords.longitude };
        setUserPos(pos); setMapCenter(pos); loadLockers(pos.lat, pos.lng);
      },
      () => setGeoError("Не удалось определить местоположение"),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  const availableUnits = (locker: LockerLocation) =>
    locker.units?.filter(u => u.status === "AVAILABLE").length || 0;

  function lockerImageUrl(locker: LockerLocation): string | null {
    if (!locker.image) return null;
    if (locker.image.startsWith("http")) return locker.image;
    const base = API_BASE.replace(/\/api\/?$/, "");
    return `${base}/uploads/${locker.image.replace(/^\//, "")}`;
  }

  return (
    <div className="px-4 md:px-6 lg:px-8 py-6 space-y-5 w-full" ref={pageTopRef}>

      {/* Geo info banner */}
      {geoBannerVisible && userPos && (
        <div className="flex items-center gap-3 bg-eco-soft text-eco rounded-[10px] px-4 py-3 text-sm">
          <Navigation className="h-4 w-4 shrink-0" />
          <span className="flex-1 font-medium">Ваше местоположение определено. Постаматы отсортированы по расстоянию.</span>
          <button
            onClick={() => { setShowGeoModal(true); }}
            className="text-accent font-semibold text-xs hover:underline shrink-0"
          >
            Отключить
          </button>
        </div>
      )}

      {geoError && (
        <div className="flex items-center gap-3 bg-warn-soft text-warn rounded-[10px] px-4 py-3 text-sm">
          <MapPinOff className="h-4 w-4 shrink-0" />
          <span className="flex-1">{geoError}</span>
          <button onClick={retryGeolocation} className="font-semibold text-xs hover:underline shrink-0">
            Повторить
          </button>
        </div>
      )}

      {/* Map */}
      <section className="bg-surface rounded-card shadow-sm overflow-hidden">
        <div className="relative h-[300px] sm:h-[380px] md:h-[460px] w-full">
          {!GOOGLE_MAPS_KEY ? (
            <div className="flex items-center justify-center h-full bg-line/30 text-ink-40 text-sm">
              Google Maps API key не настроен
            </div>
          ) : !isLoaded ? (
            <div className="flex items-center justify-center h-full bg-line/30">
              <Loader2 className="h-6 w-6 animate-spin text-ink-40" />
            </div>
          ) : (
            <GoogleMap
              mapContainerStyle={{ width: "100%", height: "100%" }}
              center={mapCenter}
              zoom={mapZoom}
              onLoad={onMapLoad}
              options={{ streetViewControl: false, mapTypeControl: false, fullscreenControl: true, zoomControl: true }}
            >
              {userPos && (
                <MarkerF
                  position={userPos}
                  icon={{
                    path: google.maps.SymbolPath.CIRCLE,
                    scale: 8,
                    fillColor: "#2E7D5B",
                    fillOpacity: 1,
                    strokeColor: "#ffffff",
                    strokeWeight: 2,
                  }}
                  title="Вы здесь"
                />
              )}
              {lockers.filter(l => l.latitude && l.longitude).map(locker => (
                <MarkerF
                  key={locker.id}
                  position={{ lat: locker.latitude!, lng: locker.longitude! }}
                  onClick={() => setSelectedLocker(locker)}
                  icon={{
                    path: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z",
                    fillColor: "#FFC629",
                    fillOpacity: 1,
                    strokeColor: "#1a1a1a",
                    strokeWeight: 1.5,
                    scale: 1.5,
                    anchor: new google.maps.Point(12, 22),
                  }}
                  title={locker.name}
                />
              ))}
              {selectedLocker && selectedLocker.latitude && selectedLocker.longitude && (
                <InfoWindowF
                  position={{ lat: selectedLocker.latitude, lng: selectedLocker.longitude }}
                  onCloseClick={() => setSelectedLocker(null)}
                >
                  <div className="p-1 max-w-[200px]">
                    <h3 className="font-semibold text-sm">{selectedLocker.name}</h3>
                    <p className="text-xs text-gray-600 mt-1">{selectedLocker.address}</p>
                    <p className="text-xs text-gray-500 mt-1">Свободных ячеек: {availableUnits(selectedLocker)}</p>
                    {selectedLocker.distance_km != null && (
                      <p className="text-xs text-blue-600 mt-1">{selectedLocker.distance_km} км от вас</p>
                    )}
                  </div>
                </InfoWindowF>
              )}
            </GoogleMap>
          )}
        </div>
      </section>

      {/* Locker list */}
      <section className="bg-surface rounded-card shadow-sm p-5">
        <div className="mb-4">
          <div className="text-[11px] font-semibold text-ink-40 uppercase tracking-wider mb-0.5">Постаматы поблизости</div>
          <h3 className="text-base font-bold text-ink-100">{lockers.length} точки в вашем районе</h3>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-ink-40" />
          </div>
        ) : lockers.length === 0 ? (
          <div className="flex flex-col items-center py-12 text-ink-40 text-sm">
            <MapPin className="h-10 w-10 text-line2 mb-3" />
            <p>Постаматы не найдены</p>
          </div>
        ) : (
          <div className="divide-y divide-line">
            {lockers.map((locker, i) => {
              const img = lockerImageUrl(locker);
              return (
                <div
                  key={locker.id}
                  onClick={() => focusLocker(locker)}
                  className={`flex items-center gap-4 py-4 cursor-pointer hover:bg-bg/60 transition-colors rounded-[10px] px-2 -mx-2 ${
                    focusedLockerId === locker.id ? 'bg-primary-soft' : ''
                  }`}
                >
                  {/* Pin number */}
                  <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-ink-100 text-sm font-extrabold shrink-0">
                    {i + 1}
                  </div>

                  {/* Image */}
                  <div className="w-14 h-14 rounded-[10px] bg-line/60 overflow-hidden flex items-center justify-center shrink-0">
                    {img
                      ? <img src={img} alt={locker.name} className="w-full h-full object-cover" />
                      : <MapPin className="h-5 w-5 text-ink-40" />
                    }
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold text-ink-100 truncate">{locker.name}</div>
                    <div className="text-xs text-ink-40 truncate mt-0.5">{locker.address}</div>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      <span className="text-xs text-ink-60">Свободных ячеек: <b>{availableUnits(locker)}</b></span>
                      {locker.distance_km != null && (
                        <>
                          <span className="text-ink-40 text-[10px]">·</span>
                          <span className="text-xs text-ink-40">{locker.distance_km} км</span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Route icon */}
                  {locker.latitude && locker.longitude && (
                    <button
                      className="w-9 h-9 rounded-[10px] bg-primary-soft flex items-center justify-center shrink-0 hover:bg-primary transition-colors"
                      aria-label="Маршрут"
                      onClick={() => { focusLocker(locker); pageTopRef.current?.scrollIntoView({ behavior: 'smooth' }) }}
                    >
                      <Navigation className="h-4 w-4 text-ink-60" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Geo modal */}
      {showGeoModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setShowGeoModal(false)}>
          <div className="bg-surface rounded-card p-6 max-w-sm w-full shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="text-base font-bold text-ink-100 mb-2">
              {userPos ? "Отключить геолокацию?" : "Включить геолокацию?"}
            </h3>
            <p className="text-sm text-ink-40 mb-5">
              {userPos
                ? "Постаматы не будут сортироваться по расстоянию."
                : "Разрешите доступ к геолокации, чтобы видеть ближайшие постаматы."}
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowGeoModal(false)}
                className="flex-1 border border-line rounded-[10px] py-2.5 text-sm font-semibold text-ink-60 hover:bg-line/60 transition-colors"
              >
                Отмена
              </button>
              <button
                onClick={userPos ? disableGeolocation : retryGeolocation}
                className="flex-1 bg-primary hover:bg-primary-hover text-ink-100 font-bold py-2.5 rounded-[10px] text-sm transition-colors"
              >
                {userPos ? "Отключить" : "Включить"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
