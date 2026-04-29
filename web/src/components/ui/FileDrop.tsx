"use client";

import { useState, useRef } from "react";
import { Upload, File, X, Database, FolderOpen } from "lucide-react";

export interface UploadedFile {
  name: string;
  size: number;
  kind?: string;
  /** 原始 File 对象 — 真实上传时携带;预置(仅元信息)时为 undefined。 */
  file?: File;
}

/**
 * 轻量级上传区 — 演示用，仅记录文件元信息，不真的上传。
 * 双态：拖拽未命中 + 拖拽命中。支持预置文件列表（"连接已有知识库"）。
 */
export function FileDrop({
  label,
  accept,
  maxFiles,
  preset,
  onChange,
  kind = "file",
  hint,
}: {
  label: string;
  accept?: string;
  maxFiles?: number;
  preset?: UploadedFile[];
  onChange?: (files: UploadedFile[]) => void;
  kind?: "file" | "kb";
  hint?: string;
}) {
  const [files, setFiles] = useState<UploadedFile[]>(preset ?? []);
  const [hover, setHover] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const push = (items: UploadedFile[]) => {
    let merged = [...files, ...items];
    if (maxFiles) merged = merged.slice(-maxFiles);
    setFiles(merged);
    onChange?.(merged);
  };

  const onBrowse = (e: React.ChangeEvent<HTMLInputElement>) => {
    const list = Array.from(e.target.files ?? []).map((f) => ({
      name: f.name,
      size: f.size,
      file: f,
    }));
    if (list.length) push(list);
    e.target.value = "";
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setHover(false);
    const list = Array.from(e.dataTransfer.files).map((f) => ({
      name: f.name,
      size: f.size,
      file: f,
    }));
    if (list.length) push(list);
  };

  const remove = (i: number) => {
    const next = files.filter((_, idx) => idx !== i);
    setFiles(next);
    onChange?.(next);
  };

  const Icon = kind === "kb" ? Database : Upload;

  return (
    <div>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setHover(true);
        }}
        onDragLeave={() => setHover(false)}
        onDrop={onDrop}
        className={`cursor-pointer border border-dashed transition-all px-4 py-5 text-center ${
          hover
            ? "border-[var(--ink)] bg-[var(--ink-04)]"
            : "border-[var(--ink-14)] hover:border-[var(--ink-48)]"
        }`}
      >
        <Icon size={18} className="mx-auto text-[var(--accent)]" />
        <div className="mt-2 text-[12px] text-[var(--ink)]">{label}</div>
        {hint && (
          <div className="mt-1 text-[10px] text-[var(--ink-48)] font-tabular">
            {hint}
          </div>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple
        onChange={onBrowse}
        className="hidden"
      />

      {files.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {files.map((f, i) => (
            <li
              key={i}
              className="flex items-center gap-2 text-[12px] group"
            >
              <File size={12} className="text-[var(--accent)] shrink-0" />
              <span className="flex-1 min-w-0 truncate text-[var(--ink)]">
                {f.name}
              </span>
              <span className="text-[10px] font-tabular text-[var(--ink-48)]">
                {f.size > 0 ? formatSize(f.size) : "已接入"}
              </span>
              <button
                onClick={() => remove(i)}
                className="opacity-0 group-hover:opacity-100 p-0.5 text-[var(--ink-48)] hover:text-[var(--t-alert)]"
              >
                <X size={11} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/**
 * 知识库连接卡片 — 展示"已接入 N 份制度"这种状态，点击展开管理。
 */
export function KBBadge({
  label,
  count,
  onClick,
}: {
  label: string;
  count: number;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 px-3 py-2.5 border border-[var(--ink-14)] hover:border-[var(--ink)] transition-all"
    >
      <FolderOpen size={14} className="text-[var(--accent)]" />
      <span className="text-[12px] text-[var(--ink)] text-left flex-1">
        {label}
      </span>
      <span className="text-[11px] font-tabular text-[var(--ink-48)]">
        {count} 份
      </span>
    </button>
  );
}
