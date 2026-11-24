// import.meta.env.BASE_URL has a trailing slash when base is unset ("/")
// but not when a subpath base is configured ("/reading"). Normalize so
// callers can always do `${base}/path` safely.
export const base = import.meta.env.BASE_URL.replace(/\/$/, '');
