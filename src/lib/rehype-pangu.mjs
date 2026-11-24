// CJK ideographs + kana + hangul.
const CJK = '一-鿿぀-ヿ가-힯㐀-䶿';
const LATIN_OR_DIGIT = 'A-Za-z0-9';

const CJK_THEN_LATIN = new RegExp(`([${CJK}])([${LATIN_OR_DIGIT}])`, 'g');
const LATIN_THEN_CJK = new RegExp(`([${LATIN_OR_DIGIT}])([${CJK}])`, 'g');

const SKIP_TAGS = new Set(['code', 'pre', 'script', 'style']);

export function panguSpace(text) {
  return text.replace(CJK_THEN_LATIN, '$1 $2').replace(LATIN_THEN_CJK, '$1 $2');
}

function walk(node, skip) {
  if (!node || typeof node !== 'object') return;
  if (node.type === 'text' && !skip) {
    node.value = panguSpace(node.value);
    return;
  }
  if (!Array.isArray(node.children)) return;
  const childSkip = skip || (node.type === 'element' && SKIP_TAGS.has(node.tagName));
  for (const child of node.children) walk(child, childSkip);
}

// Rehype plugin: inserts a space at CJK/Latin boundaries in rendered post
// bodies, skipping code blocks (and their descendants, however deeply
// nested by a syntax highlighter) so snippets and identifiers aren't
// touched.
export default function rehypePangu() {
  return (tree) => {
    walk(tree, false);
  };
}
