import { NavLink } from 'react-router-dom';
import {
  Upload,
  MessageSquare,
  Briefcase,
  FileCheck,
  LayoutDashboard,
  Zap,
} from 'lucide-react';

const links = [
  { to: '/', icon: Upload, label: 'Upload CV' },
  { to: '/chat', icon: MessageSquare, label: 'AI Chat' },
  { to: '/jobs', icon: Briefcase, label: 'Jobs' },
  { to: '/apply', icon: FileCheck, label: 'Apply' },
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
];

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-screen w-[72px] bg-[#0d1225] border-r border-[#1e293b] flex flex-col items-center py-6 z-50">
      {/* Logo */}
      <div className="mb-8 flex items-center justify-center w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400">
        <Zap className="w-5 h-5 text-white" />
      </div>

      {/* Nav Links */}
      <nav className="flex flex-col gap-2 flex-1">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `group relative flex items-center justify-center w-11 h-11 rounded-xl transition-all duration-200 ${
                isActive
                  ? 'bg-blue-500/20 text-blue-400 glow-blue'
                  : 'text-slate-500 hover:text-slate-300 hover:bg-[#1a1f35]'
              }`
            }
          >
            <Icon className="w-5 h-5" />
            {/* Tooltip */}
            <span className="absolute left-full ml-3 px-2 py-1 text-xs font-medium text-white bg-[#1a1f35] border border-[#1e293b] rounded-md opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-50">
              {label}
            </span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
