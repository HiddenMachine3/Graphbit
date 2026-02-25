type RichContentProps = {
  content: string;
  className?: string;
};

const hasHtml = (value: string) => /<\/?[a-z][\s\S]*>/i.test(value);

const toRenderableHtml = (value: string) => {
  if (hasHtml(value)) {
    return value;
  }
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br />");
};

export default function RichContent({ content, className = "" }: RichContentProps) {
  return (
    <div
      className={`text-sm text-slate-100 [&_img]:max-h-64 [&_img]:max-w-full [&_img]:rounded [&_img]:border [&_img]:border-slate-700 ${className}`}
      dangerouslySetInnerHTML={{ __html: toRenderableHtml(content || "") }}
    />
  );
}
