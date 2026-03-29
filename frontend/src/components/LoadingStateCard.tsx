import StateCardFrame from '@/components/StateCardFrame';

export default function LoadingStateCard({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <StateCardFrame tone="loading" badge="加载中" title={title} description={description}>
      <div className="flex items-center gap-3">
        <div className="h-3 w-3 animate-pulse rounded-full bg-sky-500" />
        <div className="h-3 w-3 animate-pulse rounded-full bg-sky-400 [animation-delay:120ms]" />
        <div className="h-3 w-3 animate-pulse rounded-full bg-sky-300 [animation-delay:240ms]" />
      </div>
    </StateCardFrame>
  );
}