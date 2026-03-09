"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { navigation, type NavItem } from "@/lib/navigation";
import { useApp } from "@/lib/store";

function NavLink({ item, depth = 0 }: { item: NavItem; depth?: number }) {
  const pathname = usePathname();
  const isActive = item.href === pathname;
  const [expanded, setExpanded] = useState(false);
  const hasChildren = item.children && item.children.length > 0;

  if (item.href && !hasChildren) {
    return (
      <Link
        href={item.href}
        className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] transition-colors ${
          depth > 0 ? "pl-9" : ""
        } ${
          isActive
            ? "bg-primary text-white font-semibold"
            : "text-gray-300 hover:bg-sidebar-hover hover:text-white"
        }`}
      >
        <span className="text-base w-5 text-center">{item.icon}</span>
        <span>{item.label}</span>
      </Link>
    );
  }

  // Expandable group
  return (
    <div>
      <button
        onClick={() => {
          if (hasChildren) setExpanded(!expanded);
          else if (item.href) window.location.href = item.href;
        }}
        className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] text-gray-300 hover:bg-sidebar-hover hover:text-white transition-colors ${
          depth > 0 ? "pl-9" : ""
        }`}
      >
        <span className="text-base w-5 text-center">{item.icon}</span>
        <span className="flex-1 text-left">{item.label}</span>
        {item.children && (
          <span
            className={`text-[10px] text-gray-500 transition-transform ${
              expanded ? "rotate-90" : ""
            }`}
          >
            ▶
          </span>
        )}
      </button>
      {expanded && item.children && (
        <div className="mt-0.5">
          {item.children.map((child) => (
            <NavLink key={child.id} item={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

const TEMPLATES = [
  { key: "it_company", label: "IT企業", icon: "💻" },
  { key: "retail", label: "小売業", icon: "🏪" },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { state, dispatch } = useApp();

  return (
    <aside
      className={`fixed top-0 left-0 h-screen bg-sidebar flex flex-col z-40 transition-all duration-200 ${
        collapsed ? "w-16" : "w-56"
      }`}
    >
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 h-14 border-b border-white/10">
        <span className="text-xl">⚔️</span>
        {!collapsed && (
          <span className="text-white font-bold text-sm tracking-wide">
            KATANA AI
          </span>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="ml-auto text-gray-500 hover:text-white text-xs"
        >
          {collapsed ? "▶" : "◀"}
        </button>
      </div>

      {/* Industry Selector */}
      {!collapsed && (
        <div className="px-3 pt-3 pb-2 border-b border-white/10">
          <div className="text-[10px] text-gray-500 mb-1.5 uppercase tracking-wider">業種テンプレート</div>
          <div className="flex gap-1">
            {TEMPLATES.map((t) => (
              <button
                key={t.key}
                onClick={() => dispatch({ type: "SET_TEMPLATE", template: t.key })}
                className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg text-[11px] font-medium transition-colors ${
                  state.template === t.key
                    ? "bg-primary text-white"
                    : "bg-white/10 text-gray-400 hover:bg-white/20 hover:text-white"
                }`}
              >
                <span>{t.icon}</span>
                <span>{t.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
      {collapsed && (
        <div className="flex flex-col items-center gap-1 py-2 border-b border-white/10">
          {TEMPLATES.map((t) => (
            <button
              key={t.key}
              onClick={() => dispatch({ type: "SET_TEMPLATE", template: t.key })}
              className={`text-lg ${state.template === t.key ? "opacity-100" : "opacity-40"}`}
              title={t.label}
            >
              {t.icon}
            </button>
          ))}
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {collapsed
          ? navigation.map((item) => (
              <div key={item.id} className="flex justify-center py-2">
                {item.href ? (
                  <Link
                    href={item.href}
                    className="text-lg text-gray-400 hover:text-white"
                    title={item.label}
                  >
                    {item.icon}
                  </Link>
                ) : (
                  <span
                    className="text-lg text-gray-500 cursor-default"
                    title={item.label}
                  >
                    {item.icon}
                  </span>
                )}
              </div>
            ))
          : navigation.map((item) => <NavLink key={item.id} item={item} />)}
      </nav>

      {/* User section */}
      {!collapsed && (
        <div className="border-t border-white/10 p-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center text-white text-xs font-bold">
              G
            </div>
            <div>
              <div className="text-white text-xs font-medium">GOTO</div>
              <div className="text-gray-500 text-[10px]">Owner</div>
            </div>
          </div>
          <a
            href="#"
            className="block mt-2 text-[10px] text-primary hover:underline"
          >
            ↗ 人事労務管理へ
          </a>
        </div>
      )}
    </aside>
  );
}
