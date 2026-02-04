type ResumeButtonProps = {
  onClick: () => void;
  disabled?: boolean;
};

export default function ResumeButton({ onClick, disabled = false }: ResumeButtonProps) {
  return (
    <button
      className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60"
      onClick={onClick}
      disabled={disabled}
    >
      Resume Content
    </button>
  );
}
