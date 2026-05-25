'use client';
import { Suspense, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Image from 'next/image';
import { MapPin, Camera, Plus, Minus, Check, ChevronRight, Leaf } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { collection, onSnapshot } from 'firebase/firestore';
import { getFirestoreDb } from '@/lib/firebase';
import {
  getMyProducts, getMyLockers, createCombo,
  assignComboLocker, confirmComboPlaced, uploadComboImage,
} from '@/lib/api';

function getImageUrl(img: string) {
  if (!img) return ''
  if (img.startsWith('http') || img.startsWith('blob:')) return ''
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api'
  const origin = apiUrl.replace(/\/api\/?$/, '')
  return `${origin}/uploads/${img}`
}

type Product = { id: string; name: string; weight_grams: number; original_price: number; images?: string[] };
type LockerLocation = { id: string; name: string; address: string };
type UnitStatus = { id: string; unit_number: number; status: string; temperature?: number | null; size?: string | null };
type SelectedProduct = { product_id: string; quantity: number };

// ── Wizard step indicator ─────────────────────────────────────────────────────

function WizardSteps({ steps, current }: { steps: string[]; current: number }) {
  return (
    <div className="flex items-center max-w-2xl mx-auto pb-6 w-full">
      {steps.map((label, i) => {
        const n = i + 1
        const state = current > n ? 'done' : current === n ? 'cur' : 'idle'
        return (
          <div key={label} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center gap-1.5 min-w-[72px]">
              <div
                className="grid place-items-center font-bold transition-all"
                style={{
                  width: 32, height: 32, borderRadius: '50%', fontSize: 13,
                  background: state === 'done' ? '#2E7D5B' : state === 'cur' ? '#FFC629' : '#ececea',
                  color: state === 'done' ? 'white' : state === 'cur' ? '#1a1a1a' : '#8a8a8a',
                  boxShadow: state === 'cur' ? '0 0 0 5px #FFF8E1' : 'none',
                }}
              >
                {state === 'done'
                  ? <Check size={14} strokeWidth={3} />
                  : n}
              </div>
              <span
                className="font-semibold text-center"
                style={{
                  fontSize: 11.5,
                  color: state === 'done' ? '#2E7D5B' : state === 'cur' ? '#1a1a1a' : '#8a8a8a',
                }}
              >
                {label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div
                className="flex-1 h-0.5 -mt-5 mx-[-14px]"
                style={{ background: current > n ? '#2E7D5B' : '#ececea', transition: 'background .3s' }}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Cell grid for locker selection ────────────────────────────────────────────

const UNIT_STYLE: Record<string, { bg: string; color: string; border: string }> = {
  AVAILABLE:   { bg: '#eaf6ee', color: '#1f6b40', border: '#d2ebd9' },
  RESERVED:    { bg: '#fff4d6', color: '#7a5a00', border: '#f3e2a8' },
  OCCUPIED:    { bg: '#fde9e4', color: '#8a3a2a', border: '#f3cec3' },
  MAINTENANCE: { bg: '#ecedf0', color: '#6a6a6a', border: '#d8dadd' },
}

// ── Reusable field wrapper ────────────────────────────────────────────────────

function FieldWrap({ label, hint, children }: { label: React.ReactNode; hint?: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <label className="block font-bold mb-2" style={{ fontSize: 13, color: '#1a1a1a' }}>{label}</label>
      {children}
      {hint && <p className="mt-1.5" style={{ fontSize: 11.5, color: '#8a8a8a' }}>{hint}</p>}
    </div>
  )
}

// ── Card panel wrapper ────────────────────────────────────────────────────────

function Panel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={className}
      style={{ background: '#ffffff', border: '1px solid #e1e0db', borderRadius: 14, padding: 20 }}
    >
      {children}
    </div>
  )
}

// ── Page wrapper ──────────────────────────────────────────────────────────────

export default function AddItemPageWrapper() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    }>
      <AddItemPage />
    </Suspense>
  );
}

function AddItemPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const preLockerLocationId = searchParams.get('locker_location_id') || '';
  const preLockerUnitId     = searchParams.get('locker_unit_id') || '';
  const hasPreselected = !!(preLockerLocationId && preLockerUnitId);

  // ── State ──────────────────────────────────────────────────────────────────

  const [step, setStep] = useState(0);
  const [products, setProducts] = useState<Product[]>([]);
  const [lockers, setLockers] = useState<LockerLocation[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Step 0
  const [selected, setSelected] = useState<SelectedProduct[]>([]);

  // Step 1
  const [title, setTitle]           = useState('');
  const [description, setDescription] = useState('');
  const [discountRate, setDiscountRate] = useState(30);
  const [saleDuration, setSaleDuration] = useState(3);
  const [comboImage, setComboImage]     = useState<File | null>(null);
  const [comboImagePreview, setComboImagePreview] = useState('');

  // Step 3 (locker select — non-preselected)
  const [selectedLockerId, setSelectedLockerId] = useState(preLockerLocationId);
  const [units, setUnits]           = useState<UnitStatus[]>([]);
  const [unitsLoading, setUnitsLoading] = useState(false);
  const [lockerUnitId, setLockerUnitId] = useState(preLockerUnitId);
  const unsubRef = useRef<(() => void) | null>(null);

  // Result from BE
  const [combo, setCombo] = useState<any>(null);
  const [readySecsLeft, setReadySecsLeft] = useState<number | null>(null);

  useEffect(() => {
    if (!combo?.ready_deadline) { setReadySecsLeft(null); return; }
    const deadline = new Date(combo.ready_deadline.endsWith('Z') ? combo.ready_deadline : combo.ready_deadline + 'Z').getTime();
    const tick = () => setReadySecsLeft(Math.max(0, Math.floor((deadline - Date.now()) / 1000)));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [combo?.ready_deadline]);

  const STEP_LABELS     = hasPreselected
    ? ['Продукты', 'Информация', 'Готово', 'Размещение']
    : ['Продукты', 'Информация', 'Подтверждение', 'Постамат', 'Размещение'];

  // Visual step (1-indexed for WizardSteps component)
  const visualStep = step + 1;

  // ── Data loading ───────────────────────────────────────────────────────────

  useEffect(() => {
    Promise.all([getMyProducts(), getMyLockers()])
      .then(([p, l]: any[]) => {
        setProducts(p?.data || []);
        setLockers((l?.data || []).map((loc: any) => ({ id: loc.id, name: loc.name, address: loc.address })));
        if (l?.data?.length > 0) setSelectedLockerId(l.data[0].id);
      })
      .finally(() => setLoading(false));
    return () => { unsubRef.current?.(); };
  }, []);

  useEffect(() => {
    unsubRef.current?.();
    setUnits([]);
    setLockerUnitId('');
    if (!selectedLockerId) return;

    setUnitsLoading(true);
    try {
      const db = getFirestoreDb();
      const colRef = collection(db, 'locker_locations', selectedLockerId, 'units');
      const unsub = onSnapshot(colRef, snap => {
        setUnits(snap.docs.map(d => { const data = d.data(); return { id: d.id, ...data, status: (data.status || 'AVAILABLE').toUpperCase() } as UnitStatus; }).sort((a, b) => a.unit_number - b.unit_number));
        setUnitsLoading(false);
      }, () => setUnitsLoading(false));
      unsubRef.current = unsub;
    } catch { setUnitsLoading(false); }
  }, [selectedLockerId]);

  // ── Helpers ────────────────────────────────────────────────────────────────

  function toggleProduct(id: string) {
    setSelected(prev => prev.find(p => p.product_id === id)
      ? prev.filter(p => p.product_id !== id)
      : [...prev, { product_id: id, quantity: 1 }]);
  }

  function setQty(product_id: string, qty: number) {
    setSelected(prev => prev.map(p => p.product_id === product_id ? { ...p, quantity: Math.max(1, qty) } : p));
  }

  const previewOriginal = selected.reduce((sum, s) => {
    const p = products.find(p => p.id === s.product_id);
    return sum + (p ? p.original_price * s.quantity : 0);
  }, 0);
  const previewSale   = Math.round(previewOriginal * (1 - discountRate / 100));
  const previewWeight = selected.reduce((sum, s) => {
    const p = products.find(p => p.id === s.product_id);
    return sum + (p ? p.weight_grams * s.quantity : 0);
  }, 0);

  async function uploadImageIfNeeded(comboId: string) {
    if (comboImage) await uploadComboImage(comboId, comboImage);
  }

  async function saveDraft() {
    setError(''); setSaving(true);
    try {
      const res = await createCombo({ title, description, discount_rate: discountRate, sale_duration_hours: saleDuration, products: selected });
      if (res?.data?.id) await uploadImageIfNeeded(res.data.id);
      router.push('/seller/items');
    } catch (e: any) { setError(e?.message || 'Ошибка'); }
    finally { setSaving(false); }
  }

  async function saveAndContinue() {
    setError(''); setSaving(true);
    try {
      const res = await createCombo({ title, description, discount_rate: discountRate, sale_duration_hours: saleDuration, products: selected });
      const createdCombo = res?.data;
      if (createdCombo?.id) await uploadImageIfNeeded(createdCombo.id);
      setCombo(createdCombo);
      if (hasPreselected && createdCombo) {
        const assignRes = await assignComboLocker(createdCombo.id, { locker_unit_id: preLockerUnitId, locker_location_id: preLockerLocationId });
        setCombo(assignRes?.data);
        setStep(3);
      } else { setStep(3); }
    } catch (e: any) { setError(e?.message || 'Ошибка'); }
    finally { setSaving(false); }
  }

  async function handleAssignLocker() {
    if (!lockerUnitId || !combo) return;
    setError(''); setSaving(true);
    try {
      const res = await assignComboLocker(combo.id, { locker_unit_id: lockerUnitId, locker_location_id: selectedLockerId });
      setCombo(res?.data);
      setStep(4);
    } catch (e: any) { setError(e?.message || 'Ошибка'); }
    finally { setSaving(false); }
  }

  async function handleConfirmPlaced() {
    if (!combo) return;
    setError(''); setSaving(true);
    try {
      await confirmComboPlaced(combo.id);
      router.push('/seller/items');
    } catch (e: any) { setError(e?.message || 'Ошибка'); }
    finally { setSaving(false); }
  }

  // ── Loading ────────────────────────────────────────────────────────────────

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  );

  const selectedLocker  = lockers.find(l => l.id === selectedLockerId);
  const availableCount  = units.filter(u => u.status === 'AVAILABLE').length;
  const isPlacementStep = (step === 4 && !hasPreselected) || (step === 3 && hasPreselected);

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div style={{ padding: '24px 32px 48px' }}>
      <WizardSteps steps={STEP_LABELS} current={visualStep} />

      {error && (
        <div
          className="mb-5 rounded-xl font-medium"
          style={{ background: '#FFEDE7', color: '#E8553D', padding: '12px 16px', fontSize: 14 }}
        >
          {error}
        </div>
      )}

      {/* ── Step 0: Products ──────────────────────────────────────────────── */}
      {step === 0 && (
        <div className="grid gap-6" style={{ gridTemplateColumns: '1.6fr 1fr', alignItems: 'start', maxWidth: 960, margin: '0 auto' }}>
          {/* Main */}
          <div>
            <div className="mb-5">
              <h2 className="font-extrabold m-0 mb-1" style={{ fontSize: 24, letterSpacing: '-0.02em' }}>
                Выберите продукты для набора
              </h2>
              <p className="text-ink-40 m-0" style={{ fontSize: 14, lineHeight: 1.5 }}>
                Соберите набор из непроданных продуктов. Покупатель видит только примерное описание.
              </p>
            </div>

            {products.length === 0 ? (
              <Panel>
                <div className="text-center py-8 text-ink-40">
                  <p className="font-semibold" style={{ fontSize: 14 }}>Нет продуктов</p>
                  <button onClick={() => router.push('/seller/product-management')}
                    className="mt-2 font-semibold" style={{ fontSize: 13, color: '#FFC629' }}>
                    Перейти к продуктам →
                  </button>
                </div>
              </Panel>
            ) : (
              <div className="flex flex-col gap-2">
                {products.map(p => {
                  const sel = selected.find(s => s.product_id === p.id);
                  const imgs = Array.isArray(p.images) ? p.images : [];
                  const thumb = imgs[0] ? getImageUrl(imgs[0]) : null;
                  return (
                    <div
                      key={p.id}
                      onClick={() => toggleProduct(p.id)}
                      className="flex items-center gap-3 cursor-pointer transition-colors"
                      style={{
                        padding: '12px 14px',
                        borderRadius: 11,
                        border: `1.5px solid ${sel ? '#FFC629' : '#e1e0db'}`,
                        background: sel ? '#FFF8E1' : '#ffffff',
                      }}
                      onMouseEnter={e => { if (!sel) (e.currentTarget.style.background = '#f7f6f3') }}
                      onMouseLeave={e => { if (!sel) (e.currentTarget.style.background = '#ffffff') }}
                    >
                      {/* Checkbox */}
                      <div
                        className="grid place-items-center flex-shrink-0"
                        style={{
                          width: 20, height: 20, borderRadius: 5,
                          border: `2px solid ${sel ? '#FFC629' : '#d0cec9'}`,
                          background: sel ? '#FFC629' : 'transparent',
                        }}
                      >
                        {sel && <Check size={11} strokeWidth={3} color="#1a1a1a" />}
                      </div>

                      {/* Thumbnail */}
                      <div
                        className="flex-shrink-0 overflow-hidden grid place-items-center"
                        style={{ width: 44, height: 44, borderRadius: 9, background: '#f0ede7' }}
                      >
                        {thumb ? (
                          <Image src={thumb} alt={p.name} width={44} height={44} className="object-cover w-full h-full" unoptimized />
                        ) : (
                          <Camera size={18} className="text-ink-40 opacity-50" />
                        )}
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold truncate" style={{ fontSize: 14, color: '#1a1a1a' }}>{p.name}</div>
                        <div className="text-ink-40" style={{ fontSize: 12, marginTop: 2 }}>
                          {p.weight_grams} г · {p.original_price} ₽
                        </div>
                      </div>

                      {/* Qty stepper */}
                      {sel && (
                        <div className="flex items-center gap-2 flex-shrink-0" onClick={e => e.stopPropagation()}>
                          <button
                            onClick={() => setQty(p.id, sel.quantity - 1)}
                            className="grid place-items-center font-bold transition-colors"
                            style={{ width: 28, height: 28, borderRadius: '50%', background: '#ececea', color: '#4a4a4a', fontSize: 16 }}
                            onMouseEnter={e => { (e.currentTarget.style.background = '#e1e0db') }}
                            onMouseLeave={e => { (e.currentTarget.style.background = '#ececea') }}
                          >
                            <Minus size={12} strokeWidth={2.5} />
                          </button>
                          <span className="font-bold text-center" style={{ width: 20, fontSize: 14 }}>{sel.quantity}</span>
                          <button
                            onClick={() => setQty(p.id, sel.quantity + 1)}
                            className="grid place-items-center font-bold transition-colors"
                            style={{ width: 28, height: 28, borderRadius: '50%', background: '#FFC629', color: '#1a1a1a', fontSize: 16 }}
                            onMouseEnter={e => { (e.currentTarget.style.boxShadow = '0 4px 12px rgba(255,198,41,.4)') }}
                            onMouseLeave={e => { (e.currentTarget.style.boxShadow = 'none') }}
                          >
                            <Plus size={12} strokeWidth={2.5} />
                          </button>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Sidebar summary */}
          <Panel>
            <p className="text-eyebrow text-ink-40 mb-1">Итог по набору</p>
            <h3 className="font-bold m-0 mb-4" style={{ fontSize: 17, letterSpacing: '-0.01em' }}>Состав</h3>
            <div className="flex flex-col gap-2.5">
              {[
                { label: 'Позиций', val: selected.reduce((s, i) => s + i.quantity, 0) },
                { label: 'Общий вес', val: previewWeight > 0 ? `${previewWeight} г` : '—' },
                { label: 'Розничная цена', val: previewOriginal > 0 ? `${previewOriginal} ₽` : '—' },
              ].map(row => (
                <div key={row.label} className="flex justify-between items-center" style={{ fontSize: 13 }}>
                  <span className="text-ink-60">{row.label}</span>
                  <b className="text-ink-100">{row.val}</b>
                </div>
              ))}
            </div>
            {selected.length > 0 && (
              <div
                className="mt-4 rounded-lg font-medium"
                style={{ padding: '10px 12px', background: '#FFF8E1', fontSize: 12, color: '#8a6d00', lineHeight: 1.4 }}
              >
                ⚡ На следующем шаге выберите скидку и сгенерируйте цену продажи.
              </div>
            )}
          </Panel>
        </div>
      )}
      {step === 0 && (
        <div className="flex justify-between gap-3 mt-6" style={{ maxWidth: 960, margin: '24px auto 0' }}>
          <button
            onClick={() => router.push('/seller')}
            className="font-semibold transition-colors"
            style={{ padding: '11px 20px', borderRadius: 10, fontSize: 14, background: '#ffffff', border: '1px solid #e1e0db', color: '#4a4a4a' }}
            onMouseEnter={e => { (e.currentTarget.style.background = '#f7f6f3') }}
            onMouseLeave={e => { (e.currentTarget.style.background = '#ffffff') }}
          >
            ← Отмена
          </button>
          <button
            disabled={selected.length === 0}
            onClick={() => setStep(1)}
            className="flex items-center gap-2 font-bold transition-all disabled:opacity-40"
            style={{ padding: '11px 22px', borderRadius: 10, fontSize: 14, background: '#FFC629', color: '#1a1a1a' }}
            onMouseEnter={e => { if (selected.length > 0) (e.currentTarget.style.boxShadow = '0 6px 18px rgba(255,198,41,.4)') }}
            onMouseLeave={e => { (e.currentTarget.style.boxShadow = 'none') }}
          >
            Далее: Информация <ChevronRight size={16} strokeWidth={2.2} />
          </button>
        </div>
      )}

      {/* ── Step 1: Info ──────────────────────────────────────────────────── */}
      {step === 1 && (
        <div className="grid gap-6" style={{ gridTemplateColumns: '1.6fr 1fr', alignItems: 'start', maxWidth: 960, margin: '0 auto' }}>
          {/* Main form */}
          <div>
            <div className="mb-5">
              <h2 className="font-extrabold m-0 mb-1" style={{ fontSize: 24, letterSpacing: '-0.02em' }}>Информация о наборе</h2>
              <p className="text-ink-40 m-0" style={{ fontSize: 14, lineHeight: 1.5 }}>
                Хорошее фото + честное описание = в 2 раза больше заказов.
              </p>
            </div>

            {/* Photo upload */}
            <FieldWrap label={<>Фото набора <span style={{ color: '#E8553D' }}>*</span></>}>
              <div className="flex gap-3 items-start">
                <label className="cursor-pointer flex-shrink-0">
                  <div
                    className="grid place-items-center overflow-hidden relative"
                    style={{
                      width: 120, height: 120, borderRadius: 12,
                      border: `1.5px dashed ${comboImagePreview ? '#FFC629' : '#d0cec9'}`,
                      background: comboImagePreview ? 'transparent' : '#f7f6f3',
                    }}
                  >
                    {comboImagePreview ? (
                      <Image src={comboImagePreview} alt="preview" width={120} height={120} className="object-cover w-full h-full" />
                    ) : (
                      <div className="text-center text-ink-40">
                        <Camera size={22} className="mx-auto mb-1 opacity-50" />
                        <div style={{ fontSize: 11, fontWeight: 600 }}>Добавить</div>
                      </div>
                    )}
                  </div>
                  <input type="file" accept="image/*" className="hidden" onChange={e => {
                    const file = e.target.files?.[0];
                    if (file) { setComboImage(file); setComboImagePreview(URL.createObjectURL(file)); }
                  }} />
                </label>
                {comboImagePreview && (
                  <button onClick={() => { setComboImage(null); setComboImagePreview('') }}
                    className="font-semibold" style={{ fontSize: 12, color: '#E8553D', marginTop: 8 }}>
                    Удалить
                  </button>
                )}
                <div
                  className="flex-1 rounded-lg"
                  style={{ padding: '10px 12px', background: '#f7f6f3', fontSize: 12, color: '#8a8a8a', lineHeight: 1.5 }}
                >
                  <b>Совет:</b> загрузите фото при ярком свете, крупным планом. Мин. 600×600 px.
                </div>
              </div>
            </FieldWrap>

            {/* Name */}
            <FieldWrap label={<>Название набора <span style={{ color: '#E8553D' }}>*</span></>}>
              <div className="flex items-center justify-between mb-2">
                <span />
                <span style={{ fontSize: 11.5, color: '#8a8a8a' }}>{title.length}/60</span>
              </div>
              <input
                value={title}
                onChange={e => setTitle(e.target.value)}
                maxLength={60}
                placeholder="Сэт суши на 2 персоны"
                className="w-full outline-none transition-colors"
                style={{
                  padding: '11px 14px', borderRadius: 11, fontSize: 14.5, color: '#1a1a1a',
                  background: '#ffffff', border: '1.5px solid #e1e0db',
                }}
                onFocus={e => { (e.currentTarget.style.borderColor = '#1a1a1a') }}
                onBlur={e => { (e.currentTarget.style.borderColor = '#e1e0db') }}
              />
            </FieldWrap>

            {/* Description */}
            <FieldWrap label="Описание">
              <div className="flex items-center justify-between mb-2">
                <span />
                <span style={{ fontSize: 11.5, color: '#8a8a8a' }}>{description.length}/240</span>
              </div>
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                maxLength={240}
                rows={3}
                placeholder="Свежие продукты, хранились при температуре..."
                className="w-full outline-none transition-colors resize-y"
                style={{
                  padding: '11px 14px', borderRadius: 11, fontSize: 14.5, color: '#1a1a1a',
                  background: '#ffffff', border: '1.5px solid #e1e0db',
                }}
                onFocus={e => { (e.currentTarget.style.borderColor = '#1a1a1a') }}
                onBlur={e => { (e.currentTarget.style.borderColor = '#e1e0db') }}
              />
            </FieldWrap>

            {/* Discount slider */}
            <FieldWrap label={
              <div className="flex justify-between items-center w-full">
                <span>Скидка</span>
                <span
                  className="font-extrabold rounded-full"
                  style={{ fontSize: 13, background: '#FFF8E1', color: '#8a6d00', padding: '2px 10px', borderRadius: 999 }}
                >
                  {discountRate}%
                </span>
              </div>
            }>
              <input
                type="range" min={10} max={70} step={5} value={discountRate}
                onChange={e => setDiscountRate(Number(e.target.value))}
                className="w-full"
                style={{ accentColor: '#FFC629', height: 4 }}
              />
              <div className="flex justify-between mt-1.5" style={{ fontSize: 11, color: '#8a8a8a', fontWeight: 600 }}>
                <span>10%</span><span>30%</span><span>50%</span><span>70%</span>
              </div>
            </FieldWrap>

            {/* Time slider */}
            <FieldWrap label={
              <div className="flex justify-between items-center w-full">
                <span>Время продажи</span>
                <span
                  className="font-extrabold rounded-full"
                  style={{ fontSize: 13, background: '#FFF8E1', color: '#8a6d00', padding: '2px 10px', borderRadius: 999 }}
                >
                  {saleDuration} ч.
                </span>
              </div>
            } hint={`⚡ Через ${saleDuration} ч. набор автоматически снимется с продажи, если не будет выкуплен.`}>
              <input
                type="range" min={1} max={24} value={saleDuration}
                onChange={e => setSaleDuration(Number(e.target.value))}
                className="w-full"
                style={{ accentColor: '#FFC629', height: 4 }}
              />
              <div className="flex justify-between mt-1.5" style={{ fontSize: 11, color: '#8a8a8a', fontWeight: 600 }}>
                <span>1 ч</span><span>8 ч</span><span>16 ч</span><span>24 ч</span>
              </div>
            </FieldWrap>
          </div>

          {/* Sidebar: live preview + price calc */}
          <div style={{ position: 'sticky', top: 80 }}>
            <Panel>
              <p className="text-eyebrow text-ink-40 mb-1">Превью карточки</p>
              <h3 className="font-bold m-0 mb-4" style={{ fontSize: 17, letterSpacing: '-0.01em' }}>Как видит покупатель</h3>

              {/* Preview card */}
              <div
                className="overflow-hidden mb-4"
                style={{ borderRadius: 12, border: '1px solid #e1e0db' }}
              >
                <div className="relative" style={{ aspectRatio: '4/3', background: comboImagePreview ? 'transparent' : '#f0ede7' }}>
                  {comboImagePreview ? (
                    <Image src={comboImagePreview} alt="preview" fill className="object-cover" />
                  ) : (
                    <div className="w-full h-full grid place-items-center">
                      <Camera size={28} className="text-ink-40 opacity-30" />
                    </div>
                  )}
                  <span
                    className="absolute top-2 left-2 font-bold"
                    style={{ padding: '3px 8px', borderRadius: 7, background: '#E8553D', color: 'white', fontSize: 12 }}
                  >
                    −{discountRate}%
                  </span>
                </div>
                <div style={{ padding: '10px 12px' }}>
                  <div className="font-bold truncate" style={{ fontSize: 14, color: '#1a1a1a' }}>
                    {title || 'Название набора'}
                  </div>
                  <div className="text-ink-40 mt-0.5 truncate" style={{ fontSize: 12 }}>
                    {description?.slice(0, 50) || 'Описание...'}
                  </div>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="font-extrabold" style={{ fontSize: 16, color: '#1a1a1a' }}>{previewSale} ₽</span>
                    <s className="text-ink-40" style={{ fontSize: 12 }}>{previewOriginal} ₽</s>
                  </div>
                </div>
              </div>

              {/* Price calculator */}
              <div className="flex flex-col gap-2" style={{ fontSize: 13 }}>
                {[
                  { label: 'Розничная цена', val: <s className="text-ink-40">{previewOriginal} ₽</s> },
                  { label: `Скидка ${discountRate}%`, val: <span className="text-ink-40">−{previewOriginal - previewSale} ₽</span> },
                ].map(row => (
                  <div key={row.label} className="flex justify-between">
                    <span className="text-ink-60">{row.label}</span>
                    <b>{row.val}</b>
                  </div>
                ))}
                <div style={{ height: 1, background: '#ececea', margin: '4px 0' }} />
                <div className="flex justify-between font-bold" style={{ fontSize: 15 }}>
                  <span>Цена продажи</span>
                  <span>{previewSale} ₽</span>
                </div>
                <div className="flex justify-between" style={{ color: '#2E7D5B' }}>
                  <span className="text-ink-60" style={{ fontSize: 12 }}>Ваша выручка <span title="Комиссия БережЕда 10%">(−10%)</span></span>
                  <b style={{ fontSize: 13 }}>{Math.round(previewSale * 0.9)} ₽</b>
                </div>
              </div>
            </Panel>
          </div>
        </div>
      )}
      {step === 1 && (
        <div className="flex justify-between gap-3 mt-6" style={{ maxWidth: 960, margin: '24px auto 0' }}>
          <button onClick={() => setStep(0)} className="font-semibold transition-colors"
            style={{ padding: '11px 20px', borderRadius: 10, fontSize: 14, background: '#ffffff', border: '1px solid #e1e0db', color: '#4a4a4a' }}
            onMouseEnter={e => { (e.currentTarget.style.background = '#f7f6f3') }}
            onMouseLeave={e => { (e.currentTarget.style.background = '#ffffff') }}>
            ← Назад
          </button>
          <button
            disabled={!title.trim() || !comboImage}
            onClick={() => setStep(2)}
            className="flex items-center gap-2 font-bold transition-all disabled:opacity-40"
            style={{ padding: '11px 22px', borderRadius: 10, fontSize: 14, background: '#FFC629', color: '#1a1a1a' }}
            onMouseEnter={e => { if (title.trim() && comboImage) (e.currentTarget.style.boxShadow = '0 6px 18px rgba(255,198,41,.4)') }}
            onMouseLeave={e => { (e.currentTarget.style.boxShadow = 'none') }}
          >
            Далее: Подтверждение <ChevronRight size={16} strokeWidth={2.2} />
          </button>
        </div>
      )}

      {/* ── Step 2: Confirm / Publish ─────────────────────────────────────── */}
      {step === 2 && (
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          <div className="mb-5">
            <h2 className="font-extrabold m-0 mb-1" style={{ fontSize: 24, letterSpacing: '-0.02em' }}>Проверьте перед публикацией</h2>
            <p className="text-ink-40 m-0" style={{ fontSize: 14, lineHeight: 1.5 }}>
              После публикации редактирование возможно только до первой продажи.
            </p>
          </div>

          <div className="grid gap-4 mb-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
            {/* Preview card */}
            <Panel>
              <p className="text-eyebrow text-ink-40 mb-2">Карточка</p>
              <h4 className="font-bold m-0 mb-3" style={{ fontSize: 17, letterSpacing: '-0.01em' }}>{title}</h4>
              <div
                className="overflow-hidden mb-3"
                style={{ borderRadius: 10, aspectRatio: '4/3', background: '#f0ede7' }}
              >
                {comboImagePreview && (
                  <Image src={comboImagePreview} alt="preview" width={400} height={300} className="object-cover w-full h-full" />
                )}
              </div>
              <p className="text-ink-40 m-0" style={{ fontSize: 13, lineHeight: 1.45 }}>{description || '—'}</p>
            </Panel>

            {/* Summary */}
            <div className="flex flex-col gap-3">
              <Panel>
                <p className="text-eyebrow text-ink-40 mb-2">Состав & вес</p>
                {[
                  { label: 'Позиций', val: `${selected.reduce((s, i) => s + i.quantity, 0)} шт.` },
                  { label: 'Общий вес', val: `${previewWeight} г` },
                ].map(row => (
                  <div key={row.label} className="flex justify-between py-2" style={{ fontSize: 13, borderTop: '1px solid #ececea' }}>
                    <span className="text-ink-60">{row.label}</span>
                    <b>{row.val}</b>
                  </div>
                ))}
              </Panel>

              <Panel>
                <p className="text-eyebrow text-ink-40 mb-2">Цена & время</p>
                {[
                  { label: 'Розничная цена', val: <s className="text-ink-40">{previewOriginal} ₽</s> },
                  { label: 'Скидка', val: <span style={{ color: '#E8553D' }}>−{discountRate}%</span> },
                  { label: 'Цена продажи', val: <b style={{ fontSize: 16 }}>{previewSale} ₽</b> },
                  { label: 'Окно продажи', val: `${saleDuration} ч.` },
                ].map((row, i) => (
                  <div key={i} className="flex justify-between py-2" style={{ fontSize: 13, borderTop: '1px solid #ececea' }}>
                    <span className="text-ink-60">{row.label}</span>
                    <b>{row.val}</b>
                  </div>
                ))}
              </Panel>

              {/* Eco hint */}
              <div
                className="flex items-center gap-3"
                style={{ padding: '12px 14px', borderRadius: 12, background: '#EAF3ED', border: '1px solid #c5dece' }}
              >
                <div className="grid place-items-center flex-shrink-0" style={{ width: 36, height: 36, borderRadius: 9, background: '#2E7D5B' }}>
                  <Leaf size={16} strokeWidth={1.8} color="white" />
                </div>
                <div>
                  <div className="font-bold" style={{ fontSize: 14, color: '#2E7D5B' }}>
                    ≈ {(previewWeight * 0.0025).toFixed(2)} кг CO₂
                  </div>
                  <div style={{ fontSize: 12, color: '#4a4a4a' }}>не попадёт в атмосферу</div>
                </div>
              </div>
            </div>
          </div>

          {/* Agreement */}
          <label
            className="flex items-start gap-2.5 cursor-pointer mb-5"
            style={{ fontSize: 13, color: '#4a4a4a', lineHeight: 1.5 }}
          >
            <input type="checkbox" defaultChecked className="mt-0.5 w-4 h-4" style={{ accentColor: '#1a1a1a' }} />
            <span>Подтверждаю, что состав соответствует пищевым нормам и срок годности — не менее окна продажи.</span>
          </label>

          <div className="flex justify-between gap-3">
            <button onClick={() => setStep(1)} className="font-semibold transition-colors"
              style={{ padding: '11px 20px', borderRadius: 10, fontSize: 14, background: '#ffffff', border: '1px solid #e1e0db', color: '#4a4a4a' }}
              onMouseEnter={e => { (e.currentTarget.style.background = '#f7f6f3') }}
              onMouseLeave={e => { (e.currentTarget.style.background = '#ffffff') }}>
              ← Назад
            </button>
            <div className="flex gap-2">
              {!hasPreselected && (
                <button onClick={saveDraft} disabled={saving}
                  className="font-semibold transition-colors disabled:opacity-50"
                  style={{ padding: '11px 18px', borderRadius: 10, fontSize: 14, background: '#ffffff', border: '1px solid #e1e0db', color: '#4a4a4a' }}
                  onMouseEnter={e => { if (!saving) (e.currentTarget.style.background = '#f7f6f3') }}
                  onMouseLeave={e => { (e.currentTarget.style.background = '#ffffff') }}>
                  {saving ? 'Сохранение...' : 'Черновик'}
                </button>
              )}
              <button onClick={saveAndContinue} disabled={saving}
                className="flex items-center gap-2 font-bold transition-all disabled:opacity-40"
                style={{ padding: '13px 22px', borderRadius: 12, fontSize: 14.5, background: '#FFC629', color: '#1a1a1a' }}
                onMouseEnter={e => { if (!saving) (e.currentTarget.style.boxShadow = '0 6px 18px rgba(255,198,41,.4)') }}
                onMouseLeave={e => { (e.currentTarget.style.boxShadow = 'none') }}>
                {saving ? 'Сохранение...' : hasPreselected ? 'Опубликовать →' : 'Выбрать постамат →'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Step 3: Locker unit selection (non-preselected) ───────────────── */}
      {step === 3 && !hasPreselected && (
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          <div className="mb-5">
            <h2 className="font-extrabold m-0 mb-1" style={{ fontSize: 24, letterSpacing: '-0.02em' }}>Выберите ячейку постамата</h2>
            <p className="text-ink-40 m-0" style={{ fontSize: 14 }}>Выберите свободную ячейку для размещения набора.</p>
          </div>

          {lockers.length === 0 ? (
            <Panel>
              <div className="text-center py-8 text-ink-40">
                <p className="font-semibold" style={{ fontSize: 14 }}>Нет доступных постаматов</p>
                <p style={{ fontSize: 13, marginTop: 4 }}>Обратитесь к владельцу постамата для подключения.</p>
              </div>
            </Panel>
          ) : (
            <Panel>
              {/* Locker selector */}
              <div className="mb-4">
                <p className="text-eyebrow text-ink-40 mb-2">Постамат</p>
                <select
                  value={selectedLockerId}
                  onChange={e => setSelectedLockerId(e.target.value)}
                  className="w-full outline-none"
                  style={{ padding: '10px 12px', borderRadius: 10, fontSize: 14, fontWeight: 600, color: '#1a1a1a', background: '#f7f6f3', border: '1.5px solid #e1e0db' }}
                >
                  <option value="">Выберите постамат...</option>
                  {lockers.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select>
                {selectedLocker && (
                  <div className="flex items-center gap-1.5 mt-1.5 text-ink-40" style={{ fontSize: 12 }}>
                    <MapPin size={12} /> {selectedLocker.address}
                  </div>
                )}
              </div>

              {selectedLockerId && (
                <>
                  {availableCount > 0 && (
                    <p className="mb-3" style={{ fontSize: 13, color: '#2E7D5B', fontWeight: 600 }}>
                      Свободных: {availableCount} из {units.length}
                    </p>
                  )}

                  {unitsLoading ? (
                    <div className="flex justify-center py-10">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                    </div>
                  ) : units.length === 0 ? (
                    <p className="text-center text-ink-40 py-8" style={{ fontSize: 14 }}>Нет ячеек в этом постамате</p>
                  ) : (
                    <>
                      <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${Math.min(units.length, 8)}, 1fr)`, marginBottom: 12 }}>
                        {units.map(u => {
                          const isAvailable = u.status === 'AVAILABLE';
                          const isSelected  = lockerUnitId === u.id;
                          const st = UNIT_STYLE[u.status] || UNIT_STYLE.MAINTENANCE;
                          return (
                            <div
                              key={u.id}
                              onClick={() => isAvailable && setLockerUnitId(u.id)}
                              className="flex flex-col items-center justify-center font-bold transition-transform"
                              style={{
                                aspectRatio: '1', borderRadius: 8,
                                border: `2px solid ${isSelected ? '#FFC629' : st.border}`,
                                background: isSelected ? '#FFF8E1' : st.bg,
                                color: isSelected ? '#8a6d00' : st.color,
                                cursor: isAvailable ? 'pointer' : 'not-allowed',
                                boxShadow: isSelected ? '0 0 0 3px #FFF8E1' : 'none',
                              }}
                              onMouseEnter={e => { if (isAvailable) (e.currentTarget.style.transform = 'translateY(-2px)') }}
                              onMouseLeave={e => { (e.currentTarget.style.transform = '') }}
                            >
                              <span style={{ fontSize: 16, fontWeight: 700 }}>{u.unit_number}</span>
                              {u.temperature != null && (
                                <span style={{ fontSize: 10, opacity: 0.7, marginTop: 1 }}>{u.temperature}°C</span>
                              )}
                              {isSelected && <Check size={10} strokeWidth={3} style={{ marginTop: 1 }} />}
                            </div>
                          )
                        })}
                      </div>
                      {/* Legend */}
                      <div className="flex flex-wrap gap-3 pt-2.5" style={{ borderTop: '1px solid #ececea', fontSize: 12, color: '#4a4a4a' }}>
                        {Object.entries({ AVAILABLE: 'Свободна', RESERVED: 'Забронирована', OCCUPIED: 'Занята', MAINTENANCE: 'Обслуживание' })
                          .map(([k, label]) => (
                            <span key={k} className="flex items-center gap-1.5">
                              <span className="rounded" style={{ width: 10, height: 10, background: UNIT_STYLE[k]?.bg, border: `1px solid ${UNIT_STYLE[k]?.border}`, display: 'inline-block', borderRadius: 3 }} />
                              {label}
                            </span>
                          ))}
                      </div>
                    </>
                  )}
                </>
              )}
            </Panel>
          )}

          <div className="flex justify-between gap-3 mt-6">
            <button onClick={() => { setStep(2); setCombo(null); }} className="font-semibold transition-colors"
              style={{ padding: '11px 20px', borderRadius: 10, fontSize: 14, background: '#ffffff', border: '1px solid #e1e0db', color: '#4a4a4a' }}
              onMouseEnter={e => { (e.currentTarget.style.background = '#f7f6f3') }}
              onMouseLeave={e => { (e.currentTarget.style.background = '#ffffff') }}>
              ← Назад
            </button>
            <button onClick={handleAssignLocker} disabled={!lockerUnitId || saving}
              className="flex items-center gap-2 font-bold transition-all disabled:opacity-40"
              style={{ padding: '11px 22px', borderRadius: 10, fontSize: 14, background: '#FFC629', color: '#1a1a1a' }}
              onMouseEnter={e => { if (lockerUnitId && !saving) (e.currentTarget.style.boxShadow = '0 6px 18px rgba(255,198,41,.4)') }}
              onMouseLeave={e => { (e.currentTarget.style.boxShadow = 'none') }}>
              {saving ? 'Сохранение...' : 'Подтвердить ячейку →'}
            </button>
          </div>
        </div>
      )}

      {/* ── Step 4/3: Access code + QR + confirm placed ───────────────────── */}
      {isPlacementStep && combo && (
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          <div className="grid gap-6" style={{ gridTemplateColumns: '1fr 1fr', alignItems: 'start' }}>
            {/* Left: code + QR */}
            <div>
              <div className="mb-5">
                <h2 className="font-extrabold m-0 mb-1" style={{ fontSize: 24, letterSpacing: '-0.02em' }}>Код доступа</h2>
                <p className="text-ink-40 m-0" style={{ fontSize: 14 }}>Покупатель использует этот код для получения товара.</p>
              </div>

              <Panel>
                <p className="text-eyebrow text-ink-40 mb-3">Код для покупателя</p>
                <div
                  className="font-mono font-extrabold text-center tracking-widest mb-5"
                  style={{ fontSize: 40, letterSpacing: '0.15em', color: '#1a1a1a' }}
                >
                  {combo.access_code}
                </div>
                <div className="flex justify-center mb-2">
                  <QRCodeSVG value={String(combo.access_code)} size={160} />
                </div>
              </Panel>
            </div>

            {/* Right: summary + instructions */}
            <div className="flex flex-col gap-4">
              <Panel>
                <p className="text-eyebrow text-ink-40 mb-2">Набор</p>
                {[
                  { label: 'Название', val: combo.title },
                  { label: 'Цена', val: `${combo.sale_price} ₽` },
                  { label: 'Статус', val: <span style={{ color: '#C88A1B', fontWeight: 700 }}>Готов к размещению</span> },
                ].map((row, i) => (
                  <div key={i} className="flex justify-between py-2" style={{ fontSize: 13, borderTop: '1px solid #ececea' }}>
                    <span className="text-ink-60">{row.label}</span>
                    <b>{row.val}</b>
                  </div>
                ))}
              </Panel>

              {readySecsLeft !== null && (
                <div style={{ padding: '12px 16px', borderRadius: 12, background: readySecsLeft < 120 ? '#FFEDE7' : '#f7f6f3', border: `1px solid ${readySecsLeft < 120 ? '#f3cec3' : '#e1e0db'}` }}>
                  <p className="font-bold mb-1" style={{ fontSize: 12, color: readySecsLeft < 120 ? '#E8553D' : '#4a4a4a' }}>
                    Время на размещение
                  </p>
                  <p className="font-extrabold font-mono" style={{ fontSize: 26, letterSpacing: '0.05em', color: readySecsLeft < 120 ? '#E8553D' : '#1a1a1a' }}>
                    {String(Math.floor(readySecsLeft / 60)).padStart(2, '0')}:{String(readySecsLeft % 60).padStart(2, '0')}
                  </p>
                  <p style={{ fontSize: 11.5, color: '#8a8a8a', marginTop: 2 }}>
                    Если не разместить вовремя, набор будет отменён
                  </p>
                </div>
              )}

              <div
                style={{ padding: '14px 16px', borderRadius: 12, background: '#FFF8E1', border: '1px solid #f5d97a' }}
              >
                <p className="font-bold mb-2" style={{ fontSize: 13, color: '#8a6d00' }}>Инструкция по размещению:</p>
                <ol className="list-decimal list-inside flex flex-col gap-1" style={{ fontSize: 12.5, color: '#4a4a4a' }}>
                  <li>Откройте ячейку с помощью приложения</li>
                  <li>Поместите продукты в ячейку</li>
                  <li>Закройте ячейку</li>
                  <li>Нажмите кнопку ниже для начала продажи</li>
                </ol>
              </div>
            </div>
          </div>

          <button
            onClick={handleConfirmPlaced}
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 font-bold transition-all disabled:opacity-50 mt-6"
            style={{ padding: '16px 22px', borderRadius: 12, fontSize: 15, background: '#2E7D5B', color: 'white' }}
            onMouseEnter={e => { if (!saving) (e.currentTarget.style.boxShadow = '0 6px 18px rgba(46,125,91,.35)') }}
            onMouseLeave={e => { (e.currentTarget.style.boxShadow = 'none') }}
          >
            {saving ? 'Подтверждение...' : `Я положил товар в ячейку → Начать продажу`}
          </button>
          {error && <p className="text-accent text-sm text-center mt-3">{error}</p>}
        </div>
      )}
    </div>
  );
}
