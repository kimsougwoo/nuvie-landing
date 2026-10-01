// 배포 빌드(2026-10-01): 사이트 파일을 dist/ 로 복사하고 HTML 의 주석만 걷어낸다.
// 왜: 홈 HTML 이 전송 38KB(brotli) 중 14KB 가 주석이었다(코드 설명·결정 기록). 원본에는 주석을 그대로 두고
//     배포본에서만 뺀다 — 설명은 저장소에 남고 방문자는 받지 않는다.
// 무엇을 바꾸지 않나: 글자·공백(줄바꿈 없는 공백 U+00A0·연결 문자 U+2060 포함)·JSON-LD·스크립트 동작.
//   html-minifier-terser 는 removeComments 와 인라인 JS 주석 제거(압축·이름 바꾸기 없음)만 켠다.
// 무엇을 복사하나: 저장소 파일 중 .gitignore·.vercelignore 에 걸리지 않는 것(+ 빌드 전용 파일 제외).
//   api/ 는 Vercel 이 루트에서 함수로 따로 빌드한다.
// 사용: npm run build  (Vercel buildCommand · outputDirectory = dist)   로컬 확인: node build_dist.mjs --out <폴더>
import { minify } from "html-minifier-terser";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const argOut = process.argv.indexOf("--out");
const OUT = argOut > -1 ? path.resolve(process.argv[argOut + 1]) : path.join(ROOT, "dist");

// 빌드에만 쓰는 것·사이트가 아닌 것(위치가 루트일 때)
const BUILD_ONLY = new Set(["dist", "node_modules", ".git", ".vercel", "api", "package.json", "package-lock.json",
  "build_dist.mjs", ".gitignore", ".vercelignore", "vercel.json", ".github"]);

function readPatterns(name) {
  const p = path.join(ROOT, name);
  if (!fs.existsSync(p)) return [];
  return fs.readFileSync(p, "utf8").split(/\r?\n/).map((l) => l.trim()).filter((l) => l && !l.startsWith("#"));
}
const PATTERNS = [...readPatterns(".gitignore"), ...readPatterns(".vercelignore")];

function globToRe(g) {
  return new RegExp("^" + g.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, "[^/]*").replace(/\?/g, "[^/]") + "$");
}
// gitignore 문법 중 두 파일이 쓰는 부분: 이름 글롭(어느 깊이든)·끝이 / 인 디렉터리·/ 가 든 경로 글롭
function ignored(rel, isDir) {
  const parts = rel.split("/");
  for (const pat of PATTERNS) {
    if (pat.endsWith("/")) {
      const d = pat.slice(0, -1);
      if (d.includes("/")) { if (rel === d || rel.startsWith(d + "/")) return true; continue; }
      const re = globToRe(d);
      if (parts.slice(0, isDir ? parts.length : -1).some((x) => re.test(x))) return true;
      continue;
    }
    if (pat.includes("/")) { if (globToRe(pat.replace(/^\//, "")).test(rel)) return true; continue; }
    if (globToRe(pat).test(parts[parts.length - 1])) return true;
  }
  return false;
}

// 소유 확인 파일(네이버·구글)은 글자 하나도 바꾸지 않는다
const NO_MINIFY = /^(naver[0-9a-f]+|google[0-9a-f]+)\.html$/;

const MINIFY = {
  removeComments: true,
  collapseWhitespace: false,
  minifyCSS: false,
  minifyJS: { compress: false, mangle: false, format: { comments: false } },
  decodeEntities: false,
};

const files = [];
function walk(dir) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const abs = path.join(dir, ent.name);
    const rel = path.relative(ROOT, abs).split(path.sep).join("/");
    if (!rel.includes("/") && BUILD_ONLY.has(ent.name)) continue;
    if (ignored(rel, ent.isDirectory())) continue;
    if (ent.isDirectory()) walk(abs);
    else files.push(rel);
  }
}
walk(ROOT);

fs.rmSync(OUT, { recursive: true, force: true });
let before = 0, after = 0;
for (const rel of files) {
  const src = path.join(ROOT, rel);
  const dst = path.join(OUT, rel);
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  if (rel.endsWith(".html") && !NO_MINIFY.test(rel)) {
    const html = fs.readFileSync(src, "utf8");
    const out = await minify(html, MINIFY);
    before += Buffer.byteLength(html);
    after += Buffer.byteLength(out);
    fs.writeFileSync(dst, out);
  } else {
    fs.copyFileSync(src, dst);
  }
}
console.log(`[build_dist] ${files.length} files -> ${path.relative(ROOT, OUT) || OUT} · html ${before} -> ${after} bytes`);
