// Buddy Pet Finder - 寻找传说金色闪光猫咪的 userID
// 算法逆向自 Claude Code cli.js

const crypto = require('crypto');

const SALT = "friend-2026-401";

const SPECIES = [
  "duck","goose","blob","cat","dragon","octopus","owl","penguin",
  "turtle","snail","ghost","axolotl","capybara","cactus","robot",
  "rabbit","mushroom","chonk"
];

const EYES = ["·","✦","×","◉","@","°"];
const HATS = ["none","crown","tophat","propeller","halo","wizard","beanie","tinyduck"];
const RARITY_ORDER = ["common","uncommon","rare","epic","legendary"];
const RARITY_WEIGHTS = {common:60, uncommon:25, rare:10, epic:4, legendary:1};

// FNV-1a hash
function fnv1a(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

// Mulberry32 PRNG
function mulberry32(seed) {
  let s = seed >>> 0;
  return function() {
    s |= 0;
    s = s + 1831565813 | 0;
    let t = Math.imul(s ^ s >>> 15, 1 | s);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

function pick(rng, arr) {
  return arr[Math.floor(rng() * arr.length)];
}

function getRarity(rng) {
  const total = Object.values(RARITY_WEIGHTS).reduce((a, b) => a + b, 0);
  let r = rng() * total;
  for (const level of RARITY_ORDER) {
    r -= RARITY_WEIGHTS[level];
    if (r < 0) return level;
  }
  return "common";
}

function generateBones(id) {
  const key = id + SALT;
  const hash = fnv1a(key);
  const rng = mulberry32(hash);

  const rarity = getRarity(rng);
  const species = pick(rng, SPECIES);
  const eye = pick(rng, EYES);
  const hat = rarity === "common" ? "none" : pick(rng, HATS);
  const shiny = rng() < 0.01;

  return { rarity, species, eye, hat, shiny };
}

// 目标：legendary + cat + shiny
const TARGET_RARITY = "legendary";
const TARGET_SPECIES = "cat";
const TARGET_SHINY = true;

console.log(`寻找目标: ${TARGET_RARITY} ${TARGET_SPECIES} shiny=${TARGET_SHINY}`);
console.log(`概率估算: legendary(1%) × cat(1/18≈5.6%) × shiny(1%) ≈ 1/180,000`);
console.log("开始搜索...\n");

let found = 0;
let checked = 0;
const startTime = Date.now();

// 先搜 legendary cat（不要求 shiny），概率约 1/1800
// 再搜 legendary cat shiny，概率约 1/180000
const results = { legendaryCat: [], legendaryCatShiny: [] };

for (let i = 0; i < 50_000_000; i++) {
  // 生成随机 userID (64 char hex, 类似 sha256)
  const id = crypto.createHash('sha256')
    .update(`search-${i}-${Date.now % 1000}`)
    .digest('hex');

  const bones = generateBones(id);
  checked++;

  if (bones.rarity === TARGET_RARITY && bones.species === TARGET_SPECIES) {
    const entry = { id, ...bones };
    results.legendaryCat.push(entry);

    if (bones.shiny === true) {
      results.legendaryCatShiny.push(entry);
      console.log(`\n🎉 找到传说金色闪光猫咪！`);
      console.log(`   userID: ${id}`);
      console.log(`   rarity: ${bones.rarity}, species: ${bones.species}, shiny: ${bones.shiny}`);
      console.log(`   eye: ${bones.eye}, hat: ${bones.hat}`);
      console.log(`   已搜索: ${checked.toLocaleString()} 个ID`);
      found++;
      if (found >= 3) break; // 找到3个就停
    }

    if (results.legendaryCat.length <= 5 || results.legendaryCat.length % 100 === 0) {
      console.log(`[${checked.toLocaleString()}] 找到 legendary cat (非shiny): ${id.substring(0,16)}... shiny=${bones.shiny}`);
    }
  }

  if (checked % 5_000_000 === 0) {
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`--- 进度: ${(checked/1_000_000).toFixed(0)}M 已搜索, ${results.legendaryCat.length} legendary cats, ${results.legendaryCatShiny.length} shiny, 耗时 ${elapsed}s ---`);
  }
}

const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
console.log(`\n=== 搜索完成 ===`);
console.log(`总搜索: ${checked.toLocaleString()}, 耗时: ${elapsed}s`);
console.log(`Legendary Cat: ${results.legendaryCat.length}`);
console.log(`Legendary Cat Shiny: ${results.legendaryCatShiny.length}`);

if (results.legendaryCatShiny.length > 0) {
  console.log(`\n推荐使用的 userID:`);
  console.log(results.legendaryCatShiny[0].id);
  console.log(`\n写入方法: 将此 userID 替换 ~/.claude.json 中的 userID 字段`);
} else if (results.legendaryCat.length > 0) {
  console.log(`\n未找到 shiny 版本，但找到了 legendary cat:`);
  results.legendaryCat.slice(0, 3).forEach(r => {
    console.log(`  ${r.id} (eye=${r.eye}, hat=${r.hat})`);
  });
  console.log(`\n如果不要求 shiny，可以使用上面的 ID`);
}
