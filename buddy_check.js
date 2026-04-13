// 读当前 .claude.json 里的 userID 和 accountUuid，算出各自的 BUDDY
const SALT = "friend-2026-401";
const SPECIES = ["duck","goose","blob","cat","dragon","octopus","owl","penguin","turtle","snail","ghost","axolotl","capybara","cactus","robot","rabbit","mushroom","chonk"];
const EYES = ["·","✦","×","◉","@","°"];
const HATS = ["none","crown","tophat","propeller","halo","wizard","beanie","tinyduck"];
const RARITY_ORDER = ["common","uncommon","rare","epic","legendary"];
const RARITY_WEIGHTS = {common:60,uncommon:25,rare:10,epic:4,legendary:1};

function fnv1a(s){let h=2166136261;for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619)}return h>>>0}
function mulberry32(s){let a=s>>>0;return()=>{a|=0;a=a+1831565813|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
function pick(r,a){return a[Math.floor(r()*a.length)]}
function getRarity(r){const t=Object.values(RARITY_WEIGHTS).reduce((a,b)=>a+b,0);let v=r()*t;for(const l of RARITY_ORDER){v-=RARITY_WEIGHTS[l];if(v<0)return l}return'common'}

function gen(id, label) {
  const rng = mulberry32(fnv1a(id + SALT));
  const rarity = getRarity(rng);
  const species = pick(rng, SPECIES);
  const eye = pick(rng, EYES);
  const hat = rarity === "common" ? "none" : pick(rng, HATS);
  const shiny = rng() < 0.01;
  console.log(`[${label}] ${id}`);
  console.log(`  rarity=${rarity} species=${species} eye=${eye} hat=${hat} shiny=${shiny}`);
}

gen("6059552f43ee9b53a27ba96c33251d6c5900df86c9a1550a835f7be1b668c23b", "userID");
gen("b5b3ff61-f0a6-4946-9f48-f6490e115808", "accountUuid");
