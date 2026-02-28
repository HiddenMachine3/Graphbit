type ResumeButtonProps = {
  onClick: () => void;
  disabled?: boolean;
};

export default function ResumeButton({ onClick, disabled = false }: ResumeButtonProps) {
  return (
    <button
      className="rounded bg-accent px-4 py-2 text-sm font-body text-white disabled:opacity-60 hover:bg-accent-hover transition"
      onClick={onClick}
      disabled={disabled}
    >
      Resume Content
    </button>
  );
}
