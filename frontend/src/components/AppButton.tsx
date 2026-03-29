import type { ButtonHTMLAttributes, ReactNode } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'accent' | 'ghost';
type ButtonSize = 'sm' | 'md';

const variantStyles: Record<ButtonVariant, string> = {
  primary: 'bg-ink text-white hover:bg-slate-800 disabled:bg-slate-400 disabled:text-white',
  secondary: 'border border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-white disabled:border-slate-200 disabled:text-slate-400',
  accent: 'bg-amber-500 text-white hover:bg-amber-600 disabled:bg-amber-300 disabled:text-white',
  ghost: 'border border-slate-200 bg-transparent text-slate-500 hover:border-slate-300 hover:text-slate-700 disabled:border-slate-100 disabled:text-slate-300',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-3 py-2 text-sm',
  md: 'px-5 py-3 text-sm',
};

export default function AppButton({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  loadingText,
  leftSlot,
  className = '',
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  loadingText?: string;
  leftSlot?: ReactNode;
}) {
  const isDisabled = disabled || loading;

  return (
    <button
      type="button"
      disabled={isDisabled}
      className={[
        'inline-flex items-center justify-center gap-2 rounded-full font-semibold transition',
        'disabled:cursor-not-allowed',
        variantStyles[variant],
        sizeStyles[size],
        className,
      ].join(' ')}
      {...props}
    >
      {loading ? <LoadingDot /> : leftSlot}
      <span>{loading ? (loadingText ?? children) : children}</span>
    </button>
  );
}

function LoadingDot() {
  return <span className="inline-block h-2.5 w-2.5 animate-pulse rounded-full bg-current opacity-80" />;
}