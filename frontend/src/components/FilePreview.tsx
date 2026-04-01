import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getDocumentRawUrl } from '@/services';

interface FilePreviewProps {
  docId: string;
  docType: string;
}

export default function FilePreview({ docId, docType }: FilePreviewProps) {
  const rawUrl = getDocumentRawUrl(docId);

  switch (docType) {
    case 'md':
      return <MarkdownPreview url={rawUrl} />;
    case 'txt':
      return <TextPreview url={rawUrl} />;
    case 'pdf':
      return <PdfPreview url={rawUrl} />;
    default:
      return (
        <div className="flex h-full items-center justify-center text-muted-foreground text-sm p-8">
          该文件类型（{docType}）暂不支持在线预览。
          <a href={rawUrl} download className="ml-2 text-primary underline">下载文件</a>
        </div>
      );
  }
}

function TextPreview({ url }: { url: string }) {
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setText(null);
    setError(null);
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.text();
      })
      .then(setText)
      .catch((err) => setError(err.message));
  }, [url]);

  if (error) return <p className="p-4 text-sm text-destructive">加载失败：{error}</p>;
  if (text === null) return <p className="p-4 text-sm text-muted-foreground">加载中…</p>;
  return (
    <pre className="p-4 text-xs leading-relaxed whitespace-pre-wrap break-words overflow-auto h-full">
      {text}
    </pre>
  );
}

function MarkdownPreview({ url }: { url: string }) {
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setText(null);
    setError(null);
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.text();
      })
      .then(setText)
      .catch((err) => setError(err.message));
  }, [url]);

  if (error) return <p className="p-4 text-sm text-destructive">加载失败：{error}</p>;
  if (text === null) return <p className="p-4 text-sm text-muted-foreground">加载中…</p>;
  return (
    <div className="prose prose-sm max-w-none dark:prose-invert p-4 overflow-auto h-full">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}

function PdfPreview({ url }: { url: string }) {
  return (
    <iframe
      src={url}
      title="PDF Preview"
      className="w-full h-full border-0"
    />
  );
}
