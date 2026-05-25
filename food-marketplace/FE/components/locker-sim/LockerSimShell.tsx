"use client";

import { useState, type ReactNode } from "react";
import { LogOut } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { LockerUnitsPanel } from "@/components/locker-sim/LockerUnitsPanel";
import { AddProductPane } from "@/components/locker-sim/AddProductPane";
import { logout } from "@/lib/auth";

export function LockerSimShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <div className="grid grid-cols-1 lg:grid-cols-2 min-h-screen">
        {/* Left: tabbed locker sim panel */}
        <div className="min-h-[50vh] lg:min-h-screen border-r border-divider bg-surface flex flex-col">
          {/* Header with logout */}
          <div className="flex items-center justify-between p-4 border-b border-divider">
            <h1 className="text-lg font-bold text-text">Симулятор постамата</h1>
            <button
              onClick={() => logout()}
              className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg shadow-md transition-all hover:shadow-lg active:scale-95"
            >
              <LogOut className="h-4 w-4" />
              Выйти
            </button>
          </div>

          {/* Tabs */}
          <Tabs defaultValue="home" className="flex-1 flex flex-col">
            <div className="px-4 pt-3">
              <TabsList className="w-full">
                <TabsTrigger value="home" className="flex-1">
                  Главная
                </TabsTrigger>
                <TabsTrigger value="add-product" className="flex-1">
                  Добавить продукт
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="home" className="flex-1 overflow-auto">
              <LockerUnitsPanel />
            </TabsContent>

            <TabsContent value="add-product" className="flex-1 overflow-auto">
              <AddProductPane />
            </TabsContent>
          </Tabs>
        </div>

        {/* Right: page content (scan, deposit, pickup) */}
        <div className="min-h-[50vh] lg:min-h-screen bg-background">{children}</div>
      </div>
    </div>
  );
}
