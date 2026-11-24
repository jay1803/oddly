export const CATEGORY_LABEL: Record<string, string> = {
  product: '产品',
  tool: '工具',
  model: '模型',
  idea: '点子',
  other: '其他',
};

// Tabs shown in the filter bar (default "全部" is the home feed).
export const TAB_CATEGORIES = ['product', 'tool', 'model'] as const;

export function categoryLabel(category: string): string {
  return CATEGORY_LABEL[category] ?? category;
}

export function formatDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  });
}
