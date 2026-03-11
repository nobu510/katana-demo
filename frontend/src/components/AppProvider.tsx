"use client";

import { useReducer, useEffect, useState } from "react";
import { AppContext, appReducer, type AppState } from "@/lib/store";
import { initialClients, initialStaff } from "@/lib/data";

function createInitialState(registered: boolean): AppState {
  return {
    currentMonth: 0,
    template: "it_company",
    authenticated: false,
    companyName: "",
    companyRegistered: registered,
    clients: registered ? [...initialClients] : [],
    staff: registered ? [...initialStaff] : [],
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
    // SSR時はfalse、CSR時にlocalStorageチェック
    if (typeof window === "undefined") return createInitialState(false);
    const registered = localStorage.getItem("company_registered") === "1";
    return createInitialState(registered);
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
