"use client";

import { useState, useRef } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Upload, X } from "lucide-react";

export function AddProductPane() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [weight, setWeight] = useState("");
  const [price, setPrice] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const imageError = submitted && !imageFile;
  const priceError = submitted && !price.trim();

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageFile(file);
    const url = URL.createObjectURL(file);
    setImagePreview(url);
  };

  const removeImage = () => {
    setImageFile(null);
    if (imagePreview) URL.revokeObjectURL(imagePreview);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    if (!imageFile || !price.trim()) return;

    // TODO: send to API
    alert("Продукт добавлен (симуляция)");
    // Reset
    setName("");
    setDescription("");
    setWeight("");
    setPrice("");
    removeImage();
    setSubmitted(false);
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 space-y-4">
      {/* Image upload */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-text">
          Фото продукта <span className="text-red-500">*</span>
        </label>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleImageSelect}
          className="hidden"
        />
        {imagePreview ? (
          <div className="relative w-full h-48 rounded-lg overflow-hidden border border-divider">
            <Image
              src={imagePreview}
              alt="Preview"
              fill
              className="object-cover"
            />
            <button
              type="button"
              onClick={removeImage}
              className="absolute top-2 right-2 bg-black/60 hover:bg-black/80 text-white rounded-full p-1 transition"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className={`w-full h-48 border-2 border-dashed rounded-lg flex flex-col items-center justify-center gap-2 transition ${
              imageError
                ? "border-red-400 bg-red-50"
                : "border-divider hover:border-primary hover:bg-primary/5"
            }`}
          >
            <Upload className="h-8 w-8 text-muted" />
            <span className="text-sm text-muted">Нажмите для загрузки</span>
          </button>
        )}
        {imageError && (
          <p className="text-xs text-red-500">Фото обязательно</p>
        )}
      </div>

      {/* Name */}
      <div className="space-y-1">
        <label className="text-sm font-medium text-text">Название</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full px-3 py-2 border border-divider rounded-md focus-ring text-sm"
          placeholder="Название продукта"
        />
      </div>

      {/* Description */}
      <div className="space-y-1">
        <label className="text-sm font-medium text-text">Описание</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          className="w-full px-3 py-2 border border-divider rounded-md focus-ring text-sm resize-none"
          placeholder="Описание продукта"
        />
      </div>

      {/* Weight */}
      <div className="space-y-1">
        <label className="text-sm font-medium text-text">Вес (г)</label>
        <input
          type="number"
          min="0"
          step="1"
          value={weight}
          onChange={(e) => setWeight(e.target.value)}
          className="w-full px-3 py-2 border border-divider rounded-md focus-ring text-sm"
          placeholder="500"
        />
      </div>

      {/* Price */}
      <div className="space-y-1">
        <label className="text-sm font-medium text-text">
          Цена (₽) <span className="text-red-500">*</span>
        </label>
        <input
          type="number"
          min="0"
          step="0.01"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          className={`w-full px-3 py-2 border rounded-md focus-ring text-sm ${
            priceError ? "border-red-400" : "border-divider"
          }`}
          placeholder="100"
        />
        {priceError && (
          <p className="text-xs text-red-500">Цена обязательна</p>
        )}
      </div>

      <Button type="submit" className="w-full">
        Добавить продукт
      </Button>
    </form>
  );
}
