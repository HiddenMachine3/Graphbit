type ErrorStateProps = {
  title?: string;
  message?: string;
};

export default function ErrorState({
  title = "Something went wrong",
  message = "Please try again.",
}: ErrorStateProps) {
  return (
    <div className="rounded border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
      <div className="font-semibold">{title}</div>
      <div className="mt-1 text-rose-600">{message}</div>
    </div>
  );
}
