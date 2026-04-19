import type { CaseFile } from "@/lib/mock/dispatch";
import { Segs } from "./Segs";

/** dp-col.dp-info 右栏 · mockup L3253-3265 */
export function CaseSidebar({ caseFile }: { caseFile: CaseFile }) {
  return (
    <div className="dp-col dp-info">
      <div className="hd">
        <span className="t">
          <span className="cn">{caseFile.title}</span> <em>{caseFile.titleEm}</em>
        </span>
        <span className="n">{caseFile.n}</span>
      </div>
      <div className="body">
        {caseFile.rows.map((r, i) => (
          <div key={i} className="row">
            <div className="k">{r.k}</div>
            <div className="v">
              {r.vNum}
              {r.vUnitCn ? <span className="cn">{r.vUnitCn}</span> : null}
              {r.vEm ? <em>{r.vEm}</em> : null}
            </div>
            <div className="sub">
              <Segs segs={r.sub} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
