"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Package } from "lucide-react";
import { lockerSimPickup } from "@/lib/api";
import Link from "next/link";

export default function LockerSimPage() {
  const searchParams = useSearchParams();
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [opened, setOpened] = useState(false);

  // Pre-fill code from URL param
  useEffect(() => {
    const codeParam = searchParams.get("code");
    if (codeParam) {
      setCode(codeParam);
    }
  }, [searchParams]);

  async function handleOpen() {
    if (!code.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);
    setOpened(false);
    try {
      const res = await lockerSimPickup(code.trim());
      setResult(res.data);
      setOpened(true);
    } catch (err: any) {
      setError(err.message || "Неверный код или заказ уже получен");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <Package className="h-12 w-12 text-gray-400 mx-auto mb-3" aria-hidden="true" />
          <h1 className="text-2xl font-bold text-gray-900">Симулятор постамата</h1>
          <p className="text-gray-500 text-sm mt-1">Введите код получения</p>
        </div>

        {!opened ? (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Код получения
            </label>
            <input
              type="text"
              inputMode="numeric"
              maxLength={8}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              placeholder="000000"
              className="w-full text-center text-4xl font-bold tracking-widest border-2 border-gray-200 rounded-xl px-4 py-4 focus:outline-none focus:border-yellow-400 mb-4"
            />
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl p-3 mb-4 text-center">
                {error}
              </div>
            )}
            <button
              onClick={handleOpen}
              disabled={loading || code.length < 4}
              className="w-full bg-yellow-400 hover:bg-yellow-500 disabled:opacity-40 text-black font-bold py-4 rounded-xl text-lg transition"
            >
              {loading ? "Проверка..." : "Открыть постамат"}
            </button>
            <div className="mt-4 text-center">
              <Link href="/orders" className="text-sm text-gray-400 hover:text-gray-600">
                &larr; Вернуться к заказам
              </Link>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 text-center">
            {/* Door opening animation */}
            <div className="text-7xl mb-4 animate-bounce">🔓</div>
            <h2 className="text-xl font-bold text-green-600 mb-2">Постамат открыт!</h2>
            <p className="text-gray-500 text-sm mb-6">
              Заберите ваш товар
            </p>
            <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6 text-left">
              <p className="text-xs text-green-600 font-medium">&#10003; Получение завершено</p>
              {result?.amount && (
                <p className="text-sm text-green-800 mt-1">
                  Сумма: {result.amount.toLocaleString("ru-RU")} ₽
                </p>
              )}
              {result?.completed_at && (
                <p className="text-xs text-green-600 mt-1">
                  {new Date(result.completed_at).toLocaleString("ru-RU")}
                </p>
              )}
            </div>
            <Link
              href="/orders"
              className="block w-full bg-yellow-400 hover:bg-yellow-500 text-black font-bold py-4 rounded-xl text-lg transition"
            >
              Вернуться к заказам
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
