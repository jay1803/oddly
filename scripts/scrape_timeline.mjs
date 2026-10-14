// Scrape X home timeline (For You + Following) via ego-browser.
// Usage: ego-browser nodejs scripts/scrape_timeline.mjs
// Prints JSON array of { id, author, handle, text, url, isRetweet,
// replyCount, retweetCount, likeCount } to stdout.
//
// Engagement counts (reply/retweet/like) are extracted from each tweet
// card's action buttons (data-testid="reply"/"retweet"/"like"). A
// genuinely brand-new tweet can legitimately have low counts, so this is
// a signal for the triage rules to weigh alongside other promo cues
// (CTA language, bio reading "私信/DM for business"), not a standalone
// hard filter — see references/triage-rules.md.
//
// 2026-10-14: capped at the most recent ~50 tweets total per Max's
// request ("每次看前 50 条"). Scrolls until each tab has gathered roughly
// half the cap (with a safety iteration ceiling so a slow-loading tab
// can't hang the scrape), then the final merge is hard-capped at
// MAX_TOTAL_TWEETS, preserving timeline order (first-seen = most recent).
const MAX_TOTAL_TWEETS = 50;
const MAX_PER_TAB = Math.ceil(MAX_TOTAL_TWEETS / 2);
const MAX_SCROLL_ITERATIONS = 12;

const task = await taskSpace("scrape x timeline for oddly");
const page = task.page("p1");

function extractTweets() {
  const out = [];
  const articles = document.querySelectorAll('article[data-testid="tweet"]');
  for (const art of articles) {
    try {
      const timeEl = art.querySelector('time');
      const linkEl = timeEl ? timeEl.closest('a') : null;
      const url = linkEl ? linkEl.href : null;
      const idMatch = url ? url.match(/status\/(\d+)/) : null;
      const id = idMatch ? idMatch[1] : null;
      const userNameEl = art.querySelector('[data-testid="User-Name"]');
      const userText = userNameEl ? userNameEl.innerText : '';
      const handleMatch = userText.match(/@[A-Za-z0-9_]+/);
      const handle = handleMatch ? handleMatch[0] : null;
      const authorName = userText.split('\n')[0] || null;
      const textEl = art.querySelector('[data-testid="tweetText"]');
      const text = textEl ? textEl.innerText : '';
      const socialContext = art.querySelector('[data-testid="socialContext"]');
      const retweetFlag = !!socialContext && /repost|retweet|转推/i.test(socialContext.innerText || '');

      function parseCount(t) {
        if (!t) return 0;
        t = t.trim();
        if (!t) return 0;
        const m = t.match(/^([\d.]+)([KkMm]?)$/);
        if (!m) return 0;
        let n = parseFloat(m[1]);
        if (/[Kk]/.test(m[2])) n *= 1000;
        if (/[Mm]/.test(m[2])) n *= 1000000;
        return Math.round(n);
      }
      function metricFor(testid) {
        const btn = art.querySelector('[data-testid="' + testid + '"]');
        if (!btn) return 0;
        const lines = (btn.innerText || '').split('\n').map(s => s.trim()).filter(Boolean);
        const numLine = lines.find(l => /^[\d.]+[KkMm]?$/.test(l));
        return parseCount(numLine);
      }

      const replyCount = metricFor('reply');
      const retweetCount = metricFor('retweet');
      const likeCount = metricFor('like');

      if (id && text) {
        out.push({
          id, author: authorName, handle, text, url, isRetweet: retweetFlag,
          replyCount, retweetCount, likeCount,
        });
      }
    } catch (e) {
      // skip malformed card
    }
  }
  return out;
}

async function scrapeTab(tabUrl) {
  await page.goto(tabUrl, { waitUntil: "load", timeout: 30000 });
  await page.waitForTimeout(2500);
  let items = await page.evaluate(extractTweets);
  // Scroll incrementally until we have enough tweets for this tab's share
  // of the cap, or we hit the iteration ceiling (whichever first).
  for (let i = 0; i < MAX_SCROLL_ITERATIONS && items.length < MAX_PER_TAB; i++) {
    await page.mouse.wheel(0, 1800, { label: "scroll timeline" });
    await page.waitForTimeout(900);
    items = await page.evaluate(extractTweets);
  }
  return items.slice(0, MAX_PER_TAB);
}

const forYou = await scrapeTab("https://x.com/home");

// Click "Following" tab if present, then rescrape.
try {
  await page.click("text=Following", { timeout: 5000 });
  await page.waitForTimeout(2000);
} catch (e) {}
let followingItems = await page.evaluate(extractTweets);
for (let i = 0; i < MAX_SCROLL_ITERATIONS && followingItems.length < MAX_PER_TAB; i++) {
  await page.mouse.wheel(0, 1800, { label: "scroll following timeline" });
  await page.waitForTimeout(900);
  followingItems = await page.evaluate(extractTweets);
}
followingItems = followingItems.slice(0, MAX_PER_TAB);

const merged = new Map();
for (const item of [...forYou, ...followingItems]) {
  if (!merged.has(item.id)) merged.set(item.id, item);
}

const result = Array.from(merged.values()).slice(0, MAX_TOTAL_TWEETS);

console.log(JSON.stringify(result));
console.log("===FINISH===");
console.log(JSON.stringify(await task.finish({ keep: [] })));
