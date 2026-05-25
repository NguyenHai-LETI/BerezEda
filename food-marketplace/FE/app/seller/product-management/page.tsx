'use client'
import { useEffect, useRef, useState } from 'react'
import Image from 'next/image'
import { Camera } from 'lucide-react'
import { getMyProducts, createProduct, updateProduct, deleteProduct, uploadProductImage } from '@/lib/api'
import ConfirmModal from '@/components/ConfirmModal'

function getImageUrl(img: string) {
  if (!img) return ''
  if (img.startsWith('http') || img.startsWith('blob:')) return ''
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api'
  // Strip /api suffix to get server origin, then use /uploads/ path
  const origin = apiUrl.replace(/\/api\/?$/, '')
  return `${origin}/uploads/${img}`
}

type Mode = 'list' | 'add' | 'edit'

export default function ProductManagementPage() {
  const [products, setProducts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [mode, setMode] = useState<Mode>('list')
  const [editId, setEditId] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)

  // Form fields
  const [name, setName] = useState('')
  const [weight, setWeight] = useState('')
  const [price, setPrice] = useState('')
  const [description, setDescription] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [existingImage, setExistingImage] = useState<string | null>(null)
  const [ingredients, setIngredients] = useState('')
  const [additives, setAdditives] = useState('')
  const [nutritionFacts, setNutritionFacts] = useState('')
  const [expirationDateType, setExpirationDateType] = useState('')

  const load = () => {
    setLoading(true)
    getMyProducts()
      .then(r => {
        const data = r.data || []
        data.sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        setProducts(data)
      })
      .catch(() => setProducts([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const resetForm = () => {
    setName(''); setWeight(''); setPrice(''); setDescription('')
    setIngredients(''); setAdditives(''); setNutritionFacts(''); setExpirationDateType('')
    setImageFile(null); setExistingImage(null)
    if (imagePreview) URL.revokeObjectURL(imagePreview)
    setImagePreview(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
    setSubmitted(false); setError(''); setExpanded(false)
  }

  const openAdd = () => { resetForm(); setEditId(null); setMode('add') }

  const openEdit = (p: any) => {
    resetForm()
    setEditId(p.id)
    setName(p.name || '')
    setDescription(p.description || '')
    setWeight(String(p.weight_grams || ''))
    setPrice(String(p.original_price || ''))
    setIngredients(p.ingredients || '')
    setAdditives(p.additives || '')
    setNutritionFacts(p.nutrition_facts || '')
    setExpirationDateType(p.expiration_date_type || '')
    const imgs = Array.isArray(p.images) ? p.images : []
    if (imgs.length > 0) setExistingImage(imgs[0])
    setMode('edit')
  }

  const cancel = () => { resetForm(); setMode('list') }

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImageFile(file)
    setExistingImage(null)
    setImagePreview(URL.createObjectURL(file))
  }

  const removeImage = () => {
    setImageFile(null); setExistingImage(null)
    if (imagePreview) URL.revokeObjectURL(imagePreview)
    setImagePreview(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const hasImage = !!(imageFile || existingImage)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitted(true)
    if (!name.trim() || !weight.trim() || !price.trim()) return
    if (mode === 'add' && !imageFile) return
    setSaving(true); setError('')
    try {
      const payload: any = {
        name: name.trim(),
        description: description.trim() || undefined,
        weight_grams: parseInt(weight) || 0,
        original_price: parseInt(price) || 0,
      }
      if (ingredients.trim()) payload.ingredients = ingredients.trim()
      if (additives.trim()) payload.additives = additives.trim()
      if (nutritionFacts.trim()) payload.nutrition_facts = nutritionFacts.trim()
      if (expirationDateType.trim()) payload.expiration_date_type = expirationDateType.trim()

      let productId = editId
      if (mode === 'add') {
        const res = await createProduct(payload)
        productId = res?.data?.id
      } else if (editId) {
        await updateProduct(editId, payload)
      }
      if (imageFile && productId) {
        await uploadProductImage(productId, imageFile)
      }
      resetForm()
      setMode('list')
      load()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteConfirmId) return
    const id = deleteConfirmId
    setDeleteConfirmId(null)
    try {
      await deleteProduct(id)
      load()
    } catch {}
  }

  // ── Form UI (shared for add & edit) ──
  const renderForm = () => (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-gray-700">
          {mode === 'add' ? 'Новый продукт' : 'Редактировать продукт'}
        </h2>
        <button onClick={cancel} className="text-sm text-gray-400 hover:text-gray-600">Отмена</button>
      </div>
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Image */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Фото продукта {mode === 'add' && <span className="text-red-500">*</span>}
          </label>
          <input ref={fileInputRef} type="file" accept="image/*" onChange={handleImageSelect} className="hidden" />
          {(imagePreview || existingImage) ? (
            <div className="relative w-full h-64 rounded-xl overflow-hidden border border-gray-200 bg-gray-50">
              <Image
                src={imagePreview || getImageUrl(existingImage!)}
                alt="Preview"
                fill
                className="object-contain"
                unoptimized={!!existingImage && !imagePreview}
              />
              <button type="button" onClick={removeImage}
                className="absolute top-2 right-2 bg-black/60 hover:bg-black/80 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs">
                ✕
              </button>
              <button type="button" onClick={() => fileInputRef.current?.click()}
                className="absolute bottom-2 right-2 bg-black/60 hover:bg-black/80 text-white rounded-lg px-2 py-1 text-xs">
                Заменить
              </button>
            </div>
          ) : (
            <button type="button" onClick={() => fileInputRef.current?.click()}
              className={`w-full h-64 border-2 border-dashed rounded-xl flex flex-col items-center justify-center gap-1 transition text-sm ${
                submitted && mode === 'add' && !imageFile ? 'border-red-400 bg-red-50' : 'border-gray-300 hover:border-yellow-400 hover:bg-yellow-50'
              }`}>
              <span className="text-2xl"><Camera className="h-6 w-6 text-gray-300" aria-hidden="true" /></span>
              <span className="text-gray-400">Нажмите для загрузки</span>
            </button>
          )}
          {submitted && mode === 'add' && !hasImage && <p className="text-xs text-red-500 mt-1">Фото обязательно</p>}
        </div>

        <input placeholder="Название *" value={name} onChange={e => setName(e.target.value)}
          className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-300" required />
        <input placeholder="Описание (опц.)" value={description} onChange={e => setDescription(e.target.value)}
          className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-300" />
        <div className="grid grid-cols-2 gap-3">
          <div>
            <input placeholder="Вес (г) *" type="number" value={weight} onChange={e => setWeight(e.target.value)}
              className={`w-full border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-300 ${
                submitted && !weight.trim() ? 'border-red-400' : 'border-gray-200'
              }`} />
            {submitted && !weight.trim() && <p className="text-xs text-red-500 mt-1">Обязательно</p>}
          </div>
          <div>
            <input placeholder="Цена (₽) *" type="number" value={price} onChange={e => setPrice(e.target.value)}
              className={`w-full border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-300 ${
                submitted && !price.trim() ? 'border-red-400' : 'border-gray-200'
              }`} />
            {submitted && !price.trim() && <p className="text-xs text-red-500 mt-1">Обязательно</p>}
          </div>
        </div>

        <button type="button" onClick={() => setExpanded(!expanded)}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium py-2 flex items-center gap-1">
          {expanded ? '\u25BC' : '\u25B6'} Дополнительные сведения
        </button>
        {expanded && (
          <div className="space-y-3 pl-4 border-l-2 border-yellow-200 pt-2">
            <textarea placeholder="Ингредиенты (опц.)" value={ingredients} onChange={e => setIngredients(e.target.value)}
              rows={2} className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-300" />
            <textarea placeholder="Пищевые добавки (опц.)" value={additives} onChange={e => setAdditives(e.target.value)}
              rows={1} className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-300" />
            <textarea placeholder="Пищевая ценность (опц.)" value={nutritionFacts} onChange={e => setNutritionFacts(e.target.value)}
              rows={2} className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-300" />
            <input placeholder="Тип срока годности (опц.)" value={expirationDateType} onChange={e => setExpirationDateType(e.target.value)}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-300" />
          </div>
        )}

        {error && <p className="text-red-500 text-sm">{error}</p>}
        <button type="submit" disabled={saving}
          className="w-full bg-yellow-400 hover:bg-yellow-500 disabled:opacity-40 text-black font-semibold py-3 rounded-xl transition">
          {saving ? 'Сохранение...' : mode === 'add' ? '+ Добавить продукт' : 'Сохранить изменения'}
        </button>
      </form>
    </div>
  )

  return (
    <div className="max-w-3xl mx-auto p-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Управление продуктами</h1>
        {mode === 'list' && (
          <button onClick={openAdd}
            className="bg-yellow-400 hover:bg-yellow-500 text-black font-semibold px-4 py-2 rounded-xl text-sm transition">
            + Добавить
          </button>
        )}
      </div>

      {mode !== 'list' && renderForm()}

      {/* Products list */}
      <h2 className="font-semibold text-gray-700 mb-3">Ваши продукты ({products.length})</h2>
      {loading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-400" />
        </div>
      ) : products.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p className="mb-2">Нет продуктов. Добавьте первый!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {products.map((p: any) => {
            const imgs = Array.isArray(p.images) ? p.images : []
            const thumb = imgs[0] ? getImageUrl(imgs[0]) : null
            return (
              <div key={p.id} className="bg-white rounded-xl border border-gray-100 p-3 shadow-sm">
                <div className="flex gap-3">
                  {/* Thumbnail */}
                  <div className="w-20 h-20 rounded-lg overflow-hidden bg-gray-100 shrink-0 relative">
                    {thumb ? (
                      <Image src={thumb} alt={p.name} fill className="object-cover" unoptimized />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-300 text-2xl">
                        <Camera className="h-6 w-6 text-gray-300" aria-hidden="true" />
                      </div>
                    )}
                  </div>
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-800 text-sm truncate">{p.name}</p>
                    {p.description && (
                      <p className="text-xs text-gray-400 mt-0.5 truncate">{p.description}</p>
                    )}
                    <div className="flex gap-3 mt-1 text-xs text-gray-500">
                      {p.weight_grams > 0 && <span>{p.weight_grams} г</span>}
                      {p.original_price > 0 && <span className="font-semibold text-gray-700">{p.original_price} ₽</span>}
                    </div>
                  </div>
                  {/* Actions */}
                  <div className="flex flex-col gap-1 shrink-0">
                    <button onClick={() => openEdit(p)}
                      className="text-blue-500 hover:text-blue-700 text-xs font-medium px-2 py-1 rounded hover:bg-blue-50 transition">
                      Изменить
                    </button>
                    <button onClick={() => setDeleteConfirmId(p.id)}
                      className="text-red-400 hover:text-red-600 text-xs font-medium px-2 py-1 rounded hover:bg-red-50 transition">
                      Удалить
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <ConfirmModal
        open={!!deleteConfirmId}
        title="Удалить продукт?"
        message="Продукт будет удалён. Это действие нельзя отменить."
        confirmText="Да, удалить"
        onConfirm={handleDelete}
        onCancel={() => setDeleteConfirmId(null)}
      />
    </div>
  )
}
