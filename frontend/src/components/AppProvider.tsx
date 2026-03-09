"use client";

import { useReducer } from "react";
import { AppContext, appReducer, type AppState } from "@/lib/store";
import { initialClients, initialStaff } from "@/lib/data";

const initialState: AppState = {
  currentMonth: 0,
  template: "it_company",
  registered: false,
  companyName: "",
  clients: [...initialClients],
  staff: [...initialStaff],
  messages: [],
  history: [],
  ocrAmount: 0,
  ocrDone: false,
  dashTab: "overview",
  chatOpen: false,
  typing: false,
};

export default function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}
