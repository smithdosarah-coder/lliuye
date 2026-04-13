// 搜索能产出 legendary shiny cat 的 UUID（accountUuid 格式）
const crypto = require('crypto');

const SALT = "friend-2026-401";
const SPECIES = ["duck","goose","blob","cat","dragon","octopus","owl","penguin","turtle","snail","ghost","axolotl","capybara","cactus","robot","rabbit","mushroom","chonk"];
const RARITY_ORDER = ["common","uncommon","rare","epic","legendary"];
const RARITY_WEIGHTS = {common:60,uncommon:25,rare:10,epic:4,legendary:1};
const HATS = ["none","crown","tophat","propeller","halo","wizard","beanie","tinyduck"];
const EYES = ["·","✦","×","◉","@","°"];

function fnv1a(s){let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)}return h>>>0}
function mulberry32(s){let a=s>>>0;return()=>{a|=0;a=a+1831565813|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function pick(r,a){return a[Math.floor(r()*a.length)]}
function getRarity(r){let t=100,v=r()*t;for(let l of RARITY_ORDER){v-=RARITY_WEIGHTS[l];if(v<0)return l}return'common'}

function genUUID(i) {
  // 生成 UUID v4 格式: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
  const hex = crypto.createHash('md5').update(`uuid-search-${i}`).digest('hex');
  return [
    hex.slice(0,8), hex.slice(8,12),
    '4' + hex.slice(13,16),
    ((parseInt(hex[16],16) & 0x3 | 0x8).toString(16)) + hex.slice(17,20),
    hex.slice(20,32)
  ].join('-');
}

console.log("搜索 accountUuid 格式的 legendary shiny cat...\n");
const start = Date.now();

for (let i = 0; i < 100_000_000; i++) {
  const uuid = genUUID(i);
  const key = uuid + SALT;
  const rng = mulberry32(fnv1a(key));

  const rarity = getRarity(rng);
  if (rarity !== "legendary") continue;

  const species = pick(rng, SPECIES);
  if (species !== "cat") continue;

  const eye = pick(rng, EYES);
  const hat = pick(rng, HATS);
  const shiny = rng() < 0.01;

  if (shiny) {
    console.log(`找到！UUID: ${uuid}`);
    console.log(`  rarity=${rarity} species=${species} eye=${eye} hat=${hat} shiny=${shiny}`);
    console.log(`  搜索了 ${(i+1).toLocaleString()} 个, 耗时 ${((Date.now()-start)/1000).toFixed(1)}s`);
    process.exit(0);
  }

  if (i % 10_000_000 === 0 && i > 0) {
    console.log(`进度: ${(i/1e6).toFixed(0)}M, 耗时 ${((Date.now()-start)/1000).toFixed(1)}s`);
  }
}
