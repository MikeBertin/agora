// demo-capture.js — records docs/demo.gif, the README montage of the six demos.
//
// Drives the local server through seven beats (landing → Negotiation → Auctions
// → Voting → DCOP → Supply → Matching) with Playwright + the system Chrome, records one
// continuous .webm, and prints its filename. A second ffmpeg pass turns the
// .webm into an optimised, palette-based GIF:
//
//   # 1. serve the site (see .claude/launch.json)
//   cd docs && python3 -m http.server 8761
//
//   # 2. record the webm  (needs: npm i playwright  +  Google Chrome installed)
//   node demo-capture.js                       # writes ./cap-<hash>.webm
//
//   # 3. webm -> gif  (needs ffmpeg; no dither — the flat dark UI compresses better without)
//   V=$(ls -t *.webm | head -1)
//   ffmpeg -i "$V" -vf "setpts=PTS/1.35,fps=10,scale=720:-1:flags=lanczos,palettegen=stats_mode=diff" -y palette.png
//   ffmpeg -i "$V" -i palette.png -lavfi "setpts=PTS/1.35,fps=10,scale=720:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=none:diff_mode=rectangle" -y docs/demo.gif
//
// The GIF goes stale like og.png does when a demo is added — re-record to refresh.

const { chromium } = require('playwright');

const BASE = process.env.BASE || 'http://localhost:8761';
const W = 1000, H = 740;
const OUT = process.env.OUT_DIR || '.';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function goto(page, path, scroll = 0) {
  await page.goto(BASE + path, { waitUntil: 'load' });
  await sleep(450);
  if (scroll) {
    await page.evaluate(y => window.scrollTo({ top: y }), scroll);
    await sleep(250);
  }
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({
    viewport: { width: W, height: H },
    deviceScaleFactor: 2,
    recordVideo: { dir: OUT, size: { width: W, height: H } },
  });
  const page = await context.newPage();

  // 0 — landing hero: the five cards
  await goto(page, '/');
  await sleep(1700);

  // 1 — negotiation: the bid dance against the Pareto frontier
  await goto(page, '/negotiation/', 140);
  await page.click('#playBtn');
  await sleep(3600);

  // 2 — auctions: revenue equivalence converging across four mechanisms
  await goto(page, '/auctions/', 140);
  await page.click('#playBtn');
  await sleep(3200);

  // 3 — voting: same ballots, different rules, different winners
  await goto(page, '/voting/', 120);
  await sleep(900);
  await page.selectOption('#scenario', '1');   // the spoiler effect
  await sleep(1300);
  await page.selectOption('#scenario', '2');   // the Condorcet paradox
  await sleep(1300);

  // 4 — dcop: conflicts falling round by round (autoplays on load)
  await goto(page, '/dcop/', 140);
  await sleep(3600);

  // 5 — supply: the market forms the allocation on the map, then the verdict
  await goto(page, '/supply/', 170);
  await page.click('#mMkt');                   // auto-plays from round 0
  await sleep(5200);
  await page.evaluate(() => { stopPlay(); seek(frames.length - 1); });
  await sleep(1100);

  // 6 — matching: deferred acceptance — proposals, engagements, rejections
  // (autoplays on load, one round per beat)
  await goto(page, '/matching/', 150);
  await sleep(5400);

  await context.close(); // finalizes the video
  await browser.close();

  const fs = require('fs');
  const vids = fs.readdirSync(OUT).filter(f => f.endsWith('.webm'));
  console.log('VIDEO:', vids.join(', '));
})();
