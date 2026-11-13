import React from 'react';
import { NavLink } from 'react-router-dom';
import { BookOpen, Calendar, Library } from 'lucide-react';

export const Navbar: React.FC = () => {
  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-40">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded bg-indigo-600 flex items-center justify-center text-white font-bold text-sm tracking-wide">
            VTU
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-900 tracking-tight">Study Planner</h1>
            <p className="text-[11px] text-slate-500 font-medium">Visvesvaraya Technological University</p>
          </div>
        </div>

        <nav className="flex items-center gap-1 sm:gap-2">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-slate-100 text-slate-900'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`
            }
          >
            <Calendar className="w-4 h-4" />
            <span>Planner</span>
          </NavLink>

          <NavLink
            to="/library"
            className={({ isActive }) =>
              `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs sm:text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-slate-100 text-slate-900'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`
            }
          >
            <Library className="w-4 h-4" />
            <span>Library</span>
          </NavLink>
        </nav>
      </div>
    </header>
  );
};
