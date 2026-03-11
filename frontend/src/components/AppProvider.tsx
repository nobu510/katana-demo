"use client";

import { useReducer, useEffect, useState } from "react";
import { AppContext, appReducer, type AppState } from "@/lib/store";
import { type FixedCostBreakdown } from "@/lib/data";

function createInitialState(registered: boolean): AppState {
  return {
    currentMonth: 0,
    template: "it_company",
    authenticated: false,
    companyName: "",
    companyRegistered: registered,
    industry: "",
    dataInputDone: false,
    fixedCosts: {
      personnel: 0, rent: 0, utilities: 0, communication: 0,
      lease: 0, insurance: 0, depreciation: 0, interest: 0, other: 0,
    } as FixedCostBreakdown,
    clients: [],
    staff: [],
    messages: [],
    history: [],
    ocrAmount: 0,
    ocrDone: false,
    dashTab: "overview",
    chatOpen: true,
    typing: false,
    quotes: [],
  };
}

export default function AppProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [initState] = useState<AppState>(() => {
    if (typeof window === "undefined") return createInitialState(false);
    // デモ用: 毎回オンボーディングから開始（localStorageクリア）
    localStorage.removeItem("company_registered");
    localStorage.removeItem("company_name");
    return createInitialState(false);
  });
  const [state, dispatch] = useReducer(appReducer, initState);

  useEffect(() => setReady(true), []);

  if (!ready) return null;

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}
