type ErrorStateProps = {
  title?: string;
  message?: string;
};

export default function ErrorState({
  title = "Something went wrong",
  message = "Please try again.",
}: ErrorStateProps) {
  return (
    <div className="rounded border border-pkr-low/30 bg-pkr-low/10 p-6 text-sm font-body text-pkr-low">
      <div className="font-semibold font-heading">{title}</div>
      <div className="mt-1 text-pkr-low/80">{message}</div>
    </div>
  );
}
