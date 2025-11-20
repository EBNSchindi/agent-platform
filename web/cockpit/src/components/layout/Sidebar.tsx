'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  Users,
  Inbox,
  MessageSquare,
  Zap,
  Settings,
  Mail,
  CheckSquare
} from 'lucide-react';

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  badge?: string;
  disabled?: boolean;
}

const navItems: NavItem[] = [
  { href: '/', label: 'Cockpit', icon: Home },
  { href: '/email-agent', label: 'Email-Agent', icon: Mail },
  { href: '/review-queue', label: 'Review Queue', icon: CheckSquare },
  { href: '/agents', label: 'Agents', icon: Users, badge: '3' },
  { href: '/inbox', label: 'Inbox', icon: Inbox },
  { href: '/chat', label: 'Chat', icon: MessageSquare, disabled: true },
  { href: '/automations', label: 'Automations', icon: Zap, disabled: true },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-gray-900 text-white flex flex-col">
      {/* Logo/Header */}
      <div className="p-4 border-b border-gray-800">
        <h1 className="text-xl font-bold">Agent Platform</h1>
        <p className="text-xs text-gray-400 mt-1">Mission Control</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.disabled ? '#' : item.href}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-lg transition-colors
                ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : item.disabled
                    ? 'text-gray-500 cursor-not-allowed'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }
              `}
              onClick={(e) => item.disabled && e.preventDefault()}
            >
              <Icon className="w-5 h-5" />
              <span className="flex-1">{item.label}</span>
              {item.badge && (
                <span className="text-xs bg-blue-500 px-2 py-1 rounded">
                  {item.badge}
                </span>
              )}
              {item.disabled && (
                <span className="text-xs text-gray-600">Soon</span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold">
            DT
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">Daniel Twin</p>
            <p className="text-xs text-gray-400">v1.0.0</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
