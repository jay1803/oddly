// Scrape X home timeline (For You + Following) via ego-browser.
// Usage: ego-browser nodejs scripts/scrape_timeline.mjs
// Prints JSON array of { id, author, handle, text, url, time, isReply, isRetweet } to stdout.
const task = await taskSpace("scrape x timeline for oddly");
const page = task.page("p1");

async function scrapeTab(tabUrl) {
  await page.goto(tabUrl, { waitUntil: "load", timeout: 30000 });
  await page.waitForTimeout(2500);
  // Scroll a handful of times to load more tweets.
  for (let i = 0; i < 8; i++) {
    await page.mouse.wheel(0, 1800, { label: "scroll timeline" });
    await page.waitForTimeout(900);
  }
  const items = await page.evaluate(() => {
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
        const isRetweet = art.innerText.includes('Reposted') || art.innerText.startsWith('转推') ;
        const socialContext = art.querySelector('[data-testid="socialContext"]');
        const retweetFlag = !!socialContext && /repost|retweet|转推/i.test(socialContext.innerText || '');
        if (id && text) {
          out.push({
            id,
            author: authorName,
            handle,
            text,
            url,
            isRetweet: retweetFlag,
          });
        }
      } catch (e) {
        // skip malformed card
      }
    }
    return out;
  });
  return items;
}

const forYou = await scrapeTab("https://x.com/home");
const following = await scrapeTab("https://x.com/home").catch(() => []);
// Click "Following" tab if present, then rescrape.
try {
  await page.click("text=Following", { timeout: 5000 });
  await page.waitForTimeout(2000);
  for (let i = 0; i < 6; i++) {
    await page.mouse.wheel(0, 1800, { label: "scroll following timeline" });
    await page.waitForTimeout(900);
  }
} catch (e) {}
const followingItems = await page.evaluate(() => {
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
      if (id && text) {
        out.push({ id, author: authorName, handle, text, url, isRetweet: retweetFlag });
      }
    } catch (e) {}
  }
  return out;
});

const merged = new Map();
for (const item of [...forYou, ...followingItems]) {
  if (!merged.has(item.id)) merged.set(item.id, item);
}

console.log(JSON.stringify(Array.from(merged.values())));
console.log("===FINISH===");
console.log(JSON.stringify(await task.finish({ keep: [] })));
