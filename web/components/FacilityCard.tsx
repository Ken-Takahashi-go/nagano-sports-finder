import Link from 'next/link';
import { stripFacilityCodes } from '@/lib/notes';
import { SPORT_LABEL, type FacilityWithSports } from '@/lib/types';

export function FacilityCard({ facility }: { facility: FacilityWithSports }) {
  const f = facility;
  const cleanedNotes = stripFacilityCodes(f.notes);
  return (
    <Link
      href={`/facilities/${f.facility_code}`}
      className="block bg-white border border-gray-300 rounded-lg p-4 shadow-sm hover:shadow-lg hover:border-brand-400 hover:-translate-y-0.5 transition-all duration-150"
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-bold text-gray-900 text-lg leading-tight">
          {f.facility_name}
        </h3>
        {f.lighting_available && (
          <span className="ml-2 shrink-0 text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded font-medium">
            ナイター可
          </span>
        )}
      </div>

      <div className="text-sm text-gray-600 mb-3">
        {f.municipality} {f.address && `・ ${f.address}`}
      </div>

      <div className="flex flex-wrap gap-1.5 text-xs">
        {f.sports.map((s) => (
          <span
            key={s}
            className="bg-brand-50 text-brand-700 px-2 py-0.5 rounded border border-brand-200"
          >
            {SPORT_LABEL[s]}
          </span>
        ))}
        {f.court_count !== null && (
          <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
            {f.court_count}面
          </span>
        )}
        {f.surface_type && f.surface_type !== '要確認' && (
          <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
            {f.surface_type}
          </span>
        )}
        {f.indoor_outdoor === '屋内' && (
          <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded font-medium">
            屋内
          </span>
        )}
        {f.fee_text === '無料' && (
          <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded font-medium">
            無料
          </span>
        )}
      </div>

      {cleanedNotes && (
        <p className="text-xs text-gray-500 mt-3 line-clamp-2">{cleanedNotes}</p>
      )}
    </Link>
  );
}
