import AppButton from '@/components/AppButton';
import { useUiStore } from '@/stores/uiStore';

const toneStyles = {
  success: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  error: 'border-rose-200 bg-rose-50 text-rose-900',
  info: 'border-sky-200 bg-sky-50 text-sky-900',
};

export default function ToastViewport() {
  const toasts = useUiStore((state) => state.toasts);
  const dismissToast = useUiStore((state) => state.dismissToast);

  return (
    <div className="pointer-events-none fixed right-4 top-4 z-40 flex w-[min(360px,calc(100vw-2rem))] flex-col gap-3">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`pointer-events-auto rounded-2xl border px-4 py-4 shadow-card ${toneStyles[toast.tone]}`}
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold">{toast.title}</div>
              <div className="mt-1 text-sm leading-6 opacity-90">{toast.message}</div>
            </div>
            <AppButton
              onClick={() => dismissToast(toast.id)}
              variant="ghost"
              size="sm"
              className="opacity-70 hover:opacity-100"
            >
              关闭
            </AppButton>
          </div>
        </div>
      ))}
    </div>
  );
}