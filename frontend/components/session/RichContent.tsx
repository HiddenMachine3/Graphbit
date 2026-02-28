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
      className={`text-sm font-body text-text-primary [&_img]:max-h-64 [&_img]:max-w-full [&_img]:rounded [&_img]:border [&_img]:border-border-default ${className}`}
      dangerouslySetInnerHTML={{ __html: toRenderableHtml(content || "") }}
    />
  );
}
