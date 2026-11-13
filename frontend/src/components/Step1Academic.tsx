import React, { useState } from 'react';
import { CatalogResponse, CatalogCourse } from '../types/api';
import { Search, ChevronRight } from 'lucide-react';

interface Props {
  catalog: CatalogResponse;
  data: {
    branch: string;
    year: number;
    semester: number;
    scheme: string;
    courseCode: string;
    courseTitle: string;
  };
  onChange: (field: string, val: any) => void;
  onNext: () => void;
}

export const Step1Academic: React.FC<Props> = ({ catalog, data, onChange, onNext }) => {
  const [courseSearch, setCourseSearch] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);

  // Compute allowed semesters based on Year (Y1: 1-2, Y2: 3-4, Y3: 5-6, Y4: 7-8)
  const allowedSemesters = [data.year * 2 - 1, data.year * 2];

  // Filter courses by branch, semester, scheme
  const filteredCourses = catalog.courses.filter((c) => {
    const matchBranch = !data.branch || c.branch === data.branch;
    const matchSem = !data.semester || c.semester === data.semester;
    const matchScheme = !data.scheme || c.scheme === data.scheme;
    const matchSearch =
      !courseSearch ||
      c.code.toLowerCase().includes(courseSearch.toLowerCase()) ||
      c.title.toLowerCase().includes(courseSearch.toLowerCase());
    return matchBranch && matchSem && matchScheme && matchSearch;
  });

  const handleSelectCourse = (course: CatalogCourse) => {
    onChange('courseCode', course.code);
    onChange('courseTitle', course.title);
    setCourseSearch(`${course.code} - ${course.title}`);
    setShowDropdown(false);
  };

  const handleCustomCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.toUpperCase();
    onChange('courseCode', val);
    setCourseSearch(val);
    const found = catalog.courses.find((c) => c.code.toUpperCase() === val);
    if (found) {
      onChange('courseTitle', found.title);
    }
  };

  const isFormValid =
    data.branch &&
    data.year &&
    data.semester &&
    data.scheme &&
    data.courseCode.trim().length >= 4;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-xs space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-900 tracking-tight">Academic Details</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Select your VTU department, semester, and course to tailor your study plan.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* University (Fixed) */}
        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1.5">University</label>
          <input
            type="text"
            disabled
            value="VTU (Visvesvaraya Technological University)"
            className="w-full bg-slate-50 border border-slate-200 rounded-md px-3 py-2 text-xs text-slate-600 font-medium cursor-not-allowed"
          />
        </div>

        {/* Branch */}
        <div>
          <label htmlFor="branch-select" className="block text-xs font-medium text-slate-700 mb-1.5">Branch / Stream</label>
          <select
            id="branch-select"
            value={data.branch}
            onChange={(e) => {
              onChange('branch', e.target.value);
              onChange('courseCode', '');
              onChange('courseTitle', '');
              setCourseSearch('');
            }}
            className="w-full bg-white border border-slate-300 rounded-md px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">Select Branch</option>
            {catalog.branches.map((b) => (
              <option key={b.code} value={b.code}>
                {b.name} ({b.code})
              </option>
            ))}
          </select>
        </div>

        {/* Year */}
        <div>
          <label htmlFor="year-select" className="block text-xs font-medium text-slate-700 mb-1.5">Year of Study</label>
          <select
            id="year-select"
            value={data.year}
            onChange={(e) => {
              const yr = Number(e.target.value);
              onChange('year', yr);
              onChange('semester', yr * 2 - 1); // default to first semester of year
              onChange('courseCode', '');
              onChange('courseTitle', '');
              setCourseSearch('');
            }}
            className="w-full bg-white border border-slate-300 rounded-md px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value={1}>1st Year (Sem 1 & 2)</option>
            <option value={2}>2nd Year (Sem 3 & 4)</option>
            <option value={3}>3rd Year (Sem 5 & 6)</option>
            <option value={4}>4th Year (Sem 7 & 8)</option>
          </select>
        </div>

        {/* Semester */}
        <div>
          <label htmlFor="sem-select" className="block text-xs font-medium text-slate-700 mb-1.5">Semester</label>
          <select
            id="sem-select"
            value={data.semester}
            onChange={(e) => {
              onChange('semester', Number(e.target.value));
              onChange('courseCode', '');
              onChange('courseTitle', '');
              setCourseSearch('');
            }}
            className="w-full bg-white border border-slate-300 rounded-md px-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {allowedSemesters.map((s) => (
              <option key={s} value={s}>
                Semester {s}
              </option>
            ))}
          </select>
        </div>

        {/* Scheme */}
        <div className="sm:col-span-2">
          <label className="block text-xs font-medium text-slate-700 mb-1.5">VTU Scheme</label>
          <div className="flex gap-2">
            {catalog.schemes.map((sch) => (
              <button
                key={sch}
                type="button"
                onClick={() => {
                  onChange('scheme', sch);
                  onChange('courseCode', '');
                  onChange('courseTitle', '');
                  setCourseSearch('');
                }}
                className={`flex-1 py-1.5 text-xs font-medium rounded-md border transition-all ${
                  data.scheme === sch
                    ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                    : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                }`}
              >
                {sch} Scheme
              </button>
            ))}
          </div>
        </div>

        {/* Course Code (Searchable combobox + Custom input) */}
        <div className="sm:col-span-2 relative">
          <div className="flex justify-between items-center mb-1.5">
            <label htmlFor="course-search-input" className="block text-xs font-medium text-slate-700">Course Code & Title</label>
            {data.courseTitle && (
              <span className="text-[11px] text-indigo-600 font-medium truncate max-w-[280px]">
                {data.courseTitle}
              </span>
            )}
          </div>

          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              id="course-search-input"
              type="text"
              placeholder="Search or enter course code (e.g. BCS304, 21CS52)"
              value={courseSearch || data.courseCode}
              onFocus={() => setShowDropdown(true)}
              onChange={handleCustomCodeChange}
              className="w-full bg-white border border-slate-300 rounded-md pl-9 pr-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {showDropdown && filteredCourses.length > 0 && (
            <div className="absolute z-20 w-full mt-1 bg-white border border-slate-200 rounded-md shadow-lg max-h-48 overflow-y-auto">
              {filteredCourses.map((c) => (
                <button
                  key={c.code}
                  type="button"
                  onClick={() => handleSelectCourse(c)}
                  className="w-full text-left px-3 py-2 hover:bg-indigo-50 flex items-center justify-between border-b border-slate-100 last:border-0 transition-colors"
                >
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="font-semibold text-xs text-slate-900">{c.code}</span>
                      <span className="text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-1.5 py-0.2 rounded font-medium">
                        VTU Verified
                      </span>
                    </div>
                    <span className="text-xs text-slate-600 block mt-0.5">{c.title}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded block">
                      Sem {c.semester}
                    </span>
                    {c.credits && (
                      <span className="text-[10px] text-slate-400 mt-0.5 block">
                        {c.credits} cr
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="pt-2 flex justify-end">
        <button
          type="button"
          disabled={!isFormValid}
          onClick={onNext}
          className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-medium transition-all ${
            isFormValid
              ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs'
              : 'bg-slate-100 text-slate-400 cursor-not-allowed'
          }`}
        >
          <span>Continue to Plan Options</span>
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
