"use client";

import { createContext, useContext } from "react";
import type { Client, Staff } from "./data";

export type Quote = {
  co: string;
  ps: string;
  total: number;
  tax: number;
  no: string;
  items: { n: string; q: number; p: number }[];
};

export type ChatMessage = {
  ai: boolean;
  text: string;
  actions?: { icon: string; label: string; desc?: string; href?: string }[];
};

export type AppState = {
  currentMonth: number;
  template: string;
  authenticated: boolean;
  companyName: string;
  clients: Client[];
  staff: Staff[];
  messages: ChatMessage[];
  history: { role: string; content: string }[];
  ocrAmount: number;
  ocrDone: boolean;
  dashTab: "overview" | "projects" | "staff";
  chatOpen: boolean;
  typing: boolean;
  quotes: Quote[];
};

export type AppAction =
  | { type: "SET_MONTH"; month: number }
  | { type: "SET_DASH_TAB"; tab: AppState["dashTab"] }
  | { type: "TOGGLE_CHAT" }
  | { type: "SET_CHAT_OPEN"; open: boolean }
  | { type: "ADD_MESSAGE"; message: ChatMessage }
  | { type: "ADD_HISTORY"; entry: { role: string; content: string } }
  | { type: "SET_TYPING"; typing: boolean }
  | { type: "ADD_CLIENT"; client: Client }
  | { type: "ADD_STAFF"; staff: Staff }
  | { type: "UPDATE_CLIENT"; index: number; client: Partial<Client> }
  | { type: "ADD_OCR_AMOUNT"; amount: number }
  | { type: "UPDATE_LAST_MESSAGE"; text: string }
  | { type: "LOGIN"; email: string }
  | { type: "LOGOUT" }
  | { type: "ADD_QUOTE"; quote: Quote };

export function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "SET_MONTH":
      return { ...state, currentMonth: action.month };
    case "SET_DASH_TAB":
      return { ...state, dashTab: action.tab };
    case "TOGGLE_CHAT":
      return { ...state, chatOpen: !state.chatOpen };
    case "SET_CHAT_OPEN":
      return { ...state, chatOpen: action.open };
    case "ADD_MESSAGE":
      return { ...state, messages: [...state.messages, action.message] };
    case "ADD_HISTORY":
      return { ...state, history: [...state.history, action.entry] };
    case "SET_TYPING":
      return { ...state, typing: action.typing };
    case "ADD_CLIENT":
      return { ...state, clients: [...state.clients, action.client] };
    case "ADD_STAFF":
      return { ...state, staff: [...state.staff, action.staff] };
    case "UPDATE_CLIENT": {
      const clients = [...state.clients];
      clients[action.index] = { ...clients[action.index], ...action.client };
      return { ...state, clients };
    }
    case "ADD_OCR_AMOUNT":
      return { ...state, ocrAmount: state.ocrAmount + action.amount, ocrDone: true };
    case "UPDATE_LAST_MESSAGE": {
      const msgs = [...state.messages];
      if (msgs.length > 0) msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], text: action.text };
      return { ...state, messages: msgs };
    }
    case "LOGIN":
      return { ...state, authenticated: true, companyName: action.email.split("@")[0] };
    case "LOGOUT":
      return { ...state, authenticated: false };
    case "ADD_QUOTE":
      return { ...state, quotes: [...state.quotes, action.quote] };
    default:
      return state;
  }
}

export const AppContext = createContext<{
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
} | null>(null);

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
