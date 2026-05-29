/**
 * 施設名で検索するテキストボックス。
 * 既存のクエリパラメータ (sport, surface, lighting等) は hidden input で維持。
 */
export function SearchBox({
  defaultQuery = '',
  preserveParams = {},
  size = 'normal',
  placeholder = '施設名で検索 (例: 城山)',
}: {
  defaultQuery?: string;
  preserveParams?: Record<string, string | undefined>;
  size?: 'normal' | 'large';
  placeholder?: string;
}) {
  const inputClass =
    size === 'large'
      ? 'flex-1 px-4 py-3 text-base rounded-l-lg border-2 border-r-0 border-white/30 bg-white text-gray-900 focus:outline-none focus:border-white'
      : 'flex-1 px-3 py-2 text-sm rounded-l border border-r-0 border-gray-300 focus:outline-none focus:border-brand-500';

  const buttonClass =
    size === 'large'
      ? 'px-6 py-3 bg-brand-800 hover:bg-brand-900 text-white rounded-r-lg font-medium'
      : 'px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-r text-sm font-medium';

  return (
    <form action="/search" method="get" className="flex w-full">
      <input
        type="text"
        name="q"
        defaultValue={defaultQuery}
        placeholder={placeholder}
        className={inputClass}
      />
      {/* 他のフィルタを維持するための hidden input */}
      {Object.entries(preserveParams).map(([key, value]) =>
        value ? (
          <input key={key} type="hidden" name={key} value={value} />
        ) : null,
      )}
      <button type="submit" className={buttonClass}>
        検索
      </button>
    </form>
  );
}
